import { useEffect } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import {
  ApiError,
  api,
  type Inventory,
  type Model,
  type PageRecord,
  type Rows,
  type TableRecord,
} from '@/lib/api'
import { type ModelSearch } from '@/routes/_authenticated/models/$id'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { StateCell, number } from './state'

const cell = (value: unknown) =>
  value === null || value === undefined
    ? '—'
    : typeof value === 'object'
      ? JSON.stringify(value)
      : String(value)

/** A record's address: a page file's key, or a table row's primary-key values as JSON. */
function keyOf(model: Model, keyColumns: string[], row: Record<string, unknown>) {
  return model.kind === 'page-model'
    ? String(row.key)
    : JSON.stringify(keyColumns.map((c) => row[c]))
}

const gone = (error: unknown) => error instanceof ApiError && error.status === 410

// One model: where it is defined, its state in each environment, and its records in staging.
// A versioned model's list and the records opened from it are read from one bundle version,
// held in the address, so a bundle made current in between never changes what they show.
export function ModelDetail({ id, search }: { id: string; search: ModelSearch }) {
  const navigate = useNavigate({ from: '/models/$id' })
  const inventory = useQuery({
    queryKey: ['models'],
    queryFn: () => api<Inventory>('/models'),
  })
  const model = inventory.data?.models.find((m) => m.id === id)
  const bundled = !!model && (model.kind === 'page-model' || !!model.versioned)
  const current = inventory.data?.environments.find((e) => e.name === 'staging')
    ?.bundle?.version
  const version = search.version
  const offset = search.offset ?? 0
  useEffect(() => {
    if (bundled && !version && current)
      navigate({ search: (s: ModelSearch) => ({ ...s, version: current }), replace: true })
  }, [bundled, version, current, navigate])
  const ready =
    model?.environments.staging?.status === 'present' && (!bundled || !!version)
  const rows = useQuery({
    queryKey: ['rows', id, bundled ? version : null, offset],
    queryFn: () =>
      api<Rows>(
        `/models/${encodeURIComponent(id)}/rows?offset=${offset}${bundled ? `&version=${version}` : ''}`
      ),
    enabled: ready,
    placeholderData: keepPreviousData,
    retry: (n, error) => !gone(error) && n < 2,
  })
  const data = rows.data
  const setSearch = (next: Partial<ModelSearch>) =>
    navigate({ search: (s: ModelSearch) => ({ ...s, ...next }) })
  return (
    <>
      <Header>
        <Search className='me-auto' />
        <ThemeSwitch />
        <ConfigDrawer />
      </Header>
      <Main>
        <div className='mb-4 space-y-1'>
          <Link to='/models' className='text-sm text-muted-foreground'>
            ← Models
          </Link>
          <h1 className='text-2xl font-bold tracking-tight'>
            {model?.name ?? id}
          </h1>
        </div>
        {inventory.data && !model && <p>No such model.</p>}
        {model && inventory.data && (
          <div className='space-y-4'>
            <Provenance model={model} inventory={inventory.data} />
            {gone(rows.error) && (
              <Card>
                <CardHeader>
                  <CardTitle>Bundle {version} is no longer in the store</CardTitle>
                  <CardDescription>
                    Nothing is shown from another version.{' '}
                    {current && (
                      <Link
                        to='/models/$id'
                        params={{ id }}
                        search={{ version: current }}
                        className='underline'
                      >
                        Open the current bundle, {current}
                      </Link>
                    )}
                  </CardDescription>
                </CardHeader>
              </Card>
            )}
            {data && !gone(rows.error) && (
              <Card>
                <CardHeader>
                  <CardTitle>Records in staging</CardTitle>
                  <CardDescription>
                    {number.format(data.total)} records
                    {data.version ? ` in bundle ${data.version}` : ''}
                    {data.version && current && data.version !== current
                      ? ` (not the current bundle, ${current})`
                      : ''}
                    .{' '}
                    {!!data.hiddenColumns?.length &&
                      `Never shown: ${data.hiddenColumns.join(', ')}.`}
                  </CardDescription>
                </CardHeader>
                <CardContent className='space-y-3'>
                  <div className='overflow-x-auto'>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Record</TableHead>
                          {data.columns.map((c) => (
                            <TableHead key={c.name} className='font-mono'>
                              {c.name}
                              {c.key && ' (key)'}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.rows.map((row) => {
                          const key = keyOf(model, data.key, row)
                          return (
                            <TableRow
                              key={key}
                              data-state={search.key === key ? 'selected' : undefined}
                            >
                              <TableCell>
                                <Link
                                  to='/models/$id'
                                  params={{ id }}
                                  search={{ ...search, key }}
                                  className='underline-offset-2 hover:underline'
                                >
                                  Open
                                </Link>
                              </TableCell>
                              {data.columns.map((c) => (
                                <TableCell
                                  key={c.name}
                                  className='max-w-64 truncate font-mono text-xs'
                                >
                                  {cell(row[c.name])}
                                </TableCell>
                              ))}
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                  <div className='flex items-center justify-between text-sm'>
                    <span className='text-muted-foreground'>
                      {data.total
                        ? `${number.format(offset + 1)}–${number.format(offset + data.rows.length)} of ${number.format(data.total)}`
                        : 'No records'}
                    </span>
                    <div className='space-x-2'>
                      <Button
                        variant='outline'
                        size='sm'
                        disabled={offset === 0}
                        onClick={() =>
                          setSearch({ offset: Math.max(0, offset - data.limit) || undefined })
                        }
                      >
                        Previous
                      </Button>
                      <Button
                        variant='outline'
                        size='sm'
                        disabled={offset + data.limit >= data.total}
                        onClick={() => setSearch({ offset: offset + data.limit })}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            <RecordSheet
              model={model}
              version={bundled ? version : undefined}
              recordKey={search.key}
              onClose={() => setSearch({ key: undefined })}
            />
          </div>
        )}
      </Main>
    </>
  )
}

function Provenance({ model, inventory }: { model: Model; inventory: Inventory }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Where it comes from</CardTitle>
      </CardHeader>
      <CardContent className='grid gap-4 text-sm md:grid-cols-2'>
        <dl className='grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1'>
          <dt className='text-muted-foreground'>
            {model.kind === 'table' ? 'D1 table' : 'Page model'}
          </dt>
          <dd className='font-mono'>{model.table ?? model.model}</dd>
          <dt className='text-muted-foreground'>Defined by</dt>
          <dd className='font-mono'>
            {model.migration
              ? `store/ingest/migrations/${model.migration}`
              : `the bundle's schema ${model.model}.json`}
          </dd>
          <dt className='text-muted-foreground'>Area</dt>
          <dd>{model.area}</dd>
          {model.versioned && (
            <>
              <dt className='text-muted-foreground'>Versioned</dt>
              <dd>one copy per bundle version</dd>
            </>
          )}
        </dl>
        <dl className='grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1'>
          {inventory.environments.map((e) => {
            const state = model.environments[e.name]
            return (
              <div key={e.name} className='contents'>
                <dt className='text-muted-foreground'>{e.label}</dt>
                <dd>
                  <StateCell state={state} />{' '}
                  <span className='text-muted-foreground'>
                    {state?.status === 'absent'
                      ? state.reason
                      : state?.status === 'unavailable'
                        ? e.reason
                        : state?.status === 'present' && state.version
                          ? `bundle ${state.version}`
                          : ''}
                  </span>
                </dd>
              </div>
            )
          })}
        </dl>
      </CardContent>
    </Card>
  )
}

function RecordSheet({
  model,
  version,
  recordKey,
  onClose,
}: {
  model: Model
  version?: string
  recordKey?: string
  onClose: () => void
}) {
  const page = model.kind === 'page-model'
  const record = useQuery({
    queryKey: ['record', model.id, version ?? null, recordKey],
    queryFn: () =>
      api<PageRecord | TableRecord>(
        `/models/${encodeURIComponent(model.id)}/record?key=${encodeURIComponent(recordKey ?? '')}${page && version ? `&version=${version}` : ''}`
      ),
    enabled: !!recordKey && (!page || !!version),
    retry: (n, error) => !gone(error) && n < 2,
  })
  const pageData = page ? (record.data as PageRecord | undefined) : undefined
  const tableData = !page ? (record.data as TableRecord | undefined) : undefined
  const address = tableData
    ? tableData.key.map((c, i) => `${c} = ${cell(tableData.values[i])}`).join(', ')
    : `key = ${recordKey ?? ''}`
  return (
    <Sheet open={!!recordKey} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className='w-full overflow-y-auto sm:max-w-2xl'>
        <SheetHeader>
          <SheetTitle>{model.name}</SheetTitle>
          <SheetDescription className='font-mono'>
            {model.table ?? model.model} · {address}
          </SheetDescription>
        </SheetHeader>
        <div className='space-y-3 px-4 pb-6 text-sm'>
          {gone(record.error) && (
            <p>
              Bundle {version ?? (JSON.parse(recordKey ?? '[]')[0] as string)} is no
              longer in the store, so this record is unavailable. Nothing is shown
              from another version.
            </p>
          )}
          {record.error && !gone(record.error) && (
            <p className='text-destructive'>
              {record.error instanceof ApiError && record.error.status === 404
                ? 'No such record in this bundle.'
                : String(record.error)}
            </p>
          )}
          {pageData && (
            <dl className='grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1'>
              <dt className='text-muted-foreground'>Bundle</dt>
              <dd className='font-mono'>
                {pageData.version}
                {!pageData.current && ' (not current)'}
              </dd>
              <dt className='text-muted-foreground'>Loaded</dt>
              <dd>{pageData.loaded_at}</dd>
              <dt className='text-muted-foreground'>Made by the lab</dt>
              <dd>{pageData.manifest?.made_at ?? 'not stated'}</dd>
              <dt className='text-muted-foreground'>Lab commit</dt>
              <dd className='font-mono'>
                {pageData.manifest?.lab_commit ?? 'not stated'}
              </dd>
              <dt className='text-muted-foreground'>Schema</dt>
              <dd>
                {pageData.schema ? (
                  <Badge variant='secondary'>{pageData.model}</Badge>
                ) : (
                  'none in this bundle'
                )}
              </dd>
            </dl>
          )}
          {tableData?.version && (
            <p>
              Bundle <span className='font-mono'>{tableData.version}</span>
            </p>
          )}
          {record.data && (
            <pre className='overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs'>
              {JSON.stringify(pageData ? pageData.body : tableData?.row, null, 2)}
            </pre>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
