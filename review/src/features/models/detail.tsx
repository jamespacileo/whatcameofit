import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  api,
  type Inventory,
  type Model,
  type PageRecord,
  type Rows,
} from '@/lib/api'
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

// One model: where it is defined, its state in each environment, and its records in staging.
export function ModelDetail({ id }: { id: string }) {
  const inventory = useQuery({
    queryKey: ['models'],
    queryFn: () => api<Inventory>('/models'),
  })
  const model = inventory.data?.models.find((m) => m.id === id)
  const [offset, setOffset] = useState(0)
  const [open, setOpen] = useState<Record<string, unknown> | null>(null)
  const rows = useQuery({
    queryKey: ['rows', id, offset],
    queryFn: () =>
      api<Rows>(`/models/${encodeURIComponent(id)}/rows?offset=${offset}`),
    enabled: model?.environments.staging?.status === 'present',
    placeholderData: keepPreviousData,
  })
  const data = rows.data
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
            {data && (
              <Card>
                <CardHeader>
                  <CardTitle>Records in staging</CardTitle>
                  <CardDescription>
                    {number.format(data.total)} records
                    {data.version ? ` in bundle ${data.version}` : ''}.{' '}
                    {!!data.hiddenColumns?.length &&
                      `Never shown: ${data.hiddenColumns.join(', ')}.`}
                  </CardDescription>
                </CardHeader>
                <CardContent className='space-y-3'>
                  <div className='overflow-x-auto'>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {data.columns.map((c) => (
                            <TableHead key={c.name} className='font-mono'>
                              {c.name}
                              {c.key && ' 🔑'}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.rows.map((row, i) => (
                          <TableRow
                            key={i}
                            className='cursor-pointer'
                            onClick={() => setOpen(row)}
                          >
                            {data.columns.map((c) => (
                              <TableCell
                                key={c.name}
                                className='max-w-64 truncate font-mono text-xs'
                              >
                                {cell(row[c.name])}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
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
                        onClick={() => setOffset(Math.max(0, offset - data.limit))}
                      >
                        Previous
                      </Button>
                      <Button
                        variant='outline'
                        size='sm'
                        disabled={offset + data.limit >= data.total}
                        onClick={() => setOffset(offset + data.limit)}
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
              row={open}
              columns={data?.columns ?? []}
              onClose={() => setOpen(null)}
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
  row,
  columns,
  onClose,
}: {
  model: Model
  row: Record<string, unknown> | null
  columns: Rows['columns']
  onClose: () => void
}) {
  const key = row
    ? columns
        .filter((c) => c.key)
        .map((c) => `${c.name} = ${cell(row[c.name])}`)
        .join(', ')
    : ''
  const page = useQuery({
    queryKey: ['record', model.id, row?.key],
    queryFn: () =>
      api<PageRecord>(
        `/models/${encodeURIComponent(model.id)}/record?key=${encodeURIComponent(String(row?.key))}`
      ),
    enabled: !!row && model.kind === 'page-model',
  })
  return (
    <Sheet open={!!row} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className='w-full overflow-y-auto sm:max-w-2xl'>
        <SheetHeader>
          <SheetTitle>{model.name}</SheetTitle>
          <SheetDescription className='font-mono'>
            {model.table ?? model.model} · {key || 'no key'}
          </SheetDescription>
        </SheetHeader>
        <div className='space-y-3 px-4 pb-6 text-sm'>
          {model.kind === 'page-model' && page.data && (
            <dl className='grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1'>
              <dt className='text-muted-foreground'>Bundle</dt>
              <dd className='font-mono'>{page.data.version}</dd>
              <dt className='text-muted-foreground'>Loaded</dt>
              <dd>{page.data.loaded_at}</dd>
              <dt className='text-muted-foreground'>Made by the lab</dt>
              <dd>{page.data.manifest?.made_at ?? 'not stated'}</dd>
              <dt className='text-muted-foreground'>Lab commit</dt>
              <dd className='font-mono'>
                {page.data.manifest?.lab_commit ?? 'not stated'}
              </dd>
              <dt className='text-muted-foreground'>Schema</dt>
              <dd>
                {page.data.schema ? (
                  <Badge variant='secondary'>{page.data.model}</Badge>
                ) : (
                  'none in this bundle'
                )}
              </dd>
            </dl>
          )}
          <pre className='overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs'>
            {JSON.stringify(
              model.kind === 'page-model' ? (page.data?.body ?? row) : row,
              null,
              2
            )}
          </pre>
        </div>
      </SheetContent>
    </Sheet>
  )
}
