import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { ApiError, api, type Check, type PageRow, type Pages } from '@/lib/api'
import { FILTERS, type PagesSearch } from '@/routes/_authenticated/pages'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfigDrawer } from '@/components/config-drawer'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { ThemeSwitch } from '@/components/theme-switch'
import { number } from '../models/state'

// The lab's codes for why a claim is held from a pair (PairClaimScopePage, thenwhat-lab #174),
// in the operator's words. The code itself is shown beside each, since it is what the lab wrote.
const REASONS: Record<string, string> = {
  indication_not_a_mesh_term: "The claim's indication is not one MeSH term",
  indication_names_several_records: "The claim's indication names several descriptors",
  no_pair_for_the_indication: 'No pair of this treatment for the indication',
  claim_trials_not_held: "The claim's trials are not held",
  trial_not_held: 'A trial the pair shows is not held',
  purpose_not_coded: 'A trial has no coded primary purpose',
  claim_purposes_differ: "The claim's trials have different primary purposes",
  purpose_differs: "A trial the pair shows has another primary purpose",
  population_differs: "A trial the pair shows is of another age range",
  pair_not_shown: 'Verified, but the pair is not shown yet',
}

const LABELS: Record<(typeof FILTERS)[number], string> = {
  all: 'All',
  pairs: 'Pairs',
  kept: 'Kept pages',
  redirects: 'Redirects',
  gone: 'Gone',
  held: 'Held',
  differs: 'Lab and site differ',
}

const shows: Record<(typeof FILTERS)[number], (row: PageRow) => boolean> = {
  all: () => true,
  pairs: (r) => r.kind === 'pair',
  kept: (r) => r.site?.status === 200,
  redirects: (r) => r.site?.status === 301,
  gone: (r) => r.site?.status === 410,
  held: (r) => r.lab?.scope === 'held' || !!r.heldFrom,
  differs: (r) => !!r.differs,
}

const gone = (error: unknown) => error instanceof ApiError && error.status === 410
const PAGE = 100

function SiteCell({ row }: { row: PageRow }) {
  if (row.kind === 'pair') return <Badge variant='secondary'>pair page</Badge>
  const site = row.site
  if (!site) return <span className='text-muted-foreground'>not in staging's files</span>
  return (
    <span>
      <Badge variant={site.status === 200 ? 'default' : 'outline'}>{site.status}</Badge>{' '}
      {site.answer}
      {site.to && <span className='font-mono'> {site.to}</span>}
      {site.on && <span className='text-muted-foreground'> on {site.on}</span>}
    </span>
  )
}

function LabCell({ row }: { row: PageRow }) {
  const lab = row.lab
  if (row.kind === 'pair') return null
  if (!lab) return <span className='text-muted-foreground'>not in the lab's scope</span>
  return lab.scope === 'verified' ? (
    <span>
      verified for <span className='font-mono'>{lab.pair}</span>
    </span>
  ) : (
    <span>
      held{lab.pair && <> from <span className='font-mono'>{lab.pair}</span></>}
      {lab.reason && <span className='text-muted-foreground'> ({lab.reason})</span>}
    </span>
  )
}

// Every address the public site answers for a pair or an old claim, read from staging's store
// (one bundle version, held in the address) and from the files staging was published with. A
// held claim is shown with its own page and, beside it, the pair it would lead to: never as a
// redirect neither source made.
export function PagesView({ search }: { search: PagesSearch }) {
  const navigate = useNavigate({ from: '/pages/' })
  const setSearch = (next: Partial<PagesSearch>) =>
    navigate({ search: (s: PagesSearch) => ({ ...s, ...next }), replace: true })
  const version = search.version
  const pages = useQuery({
    queryKey: ['pages', version ?? null],
    queryFn: () => api<Pages>(`/pages${version ? `?version=${version}` : ''}`),
    retry: (n, error) => !gone(error) && n < 2,
  })
  // Bound to the bundle the first answer read, so the list and the sheet stay on it.
  useEffect(() => {
    if (!version && pages.data?.version)
      navigate({ search: (s: PagesSearch) => ({ ...s, version: pages.data.version ?? undefined }), replace: true })
  }, [version, pages.data?.version, navigate])
  const show = search.show ?? 'all'
  const [words, setWords] = useState(search.q ?? '')
  const [limit, setLimit] = useState(PAGE)
  const rows = useMemo(() => {
    const q = (search.q ?? '').toLowerCase()
    return (pages.data?.rows ?? []).filter(
      (r) =>
        shows[show](r) &&
        (!q ||
          r.address.toLowerCase().includes(q) ||
          (r.title ?? '').toLowerCase().includes(q))
    )
  }, [pages.data, show, search.q])
  const open = pages.data?.rows.find((r) => r.address === search.address)
  const data = pages.data
  return (
    <>
      <Header>
        <Search className='me-auto' />
        <ThemeSwitch />
        <ConfigDrawer />
      </Header>
      <Main>
        <div className='mb-4 space-y-1'>
          <h1 className='text-2xl font-bold tracking-tight'>Pages</h1>
          <p className='text-muted-foreground'>
            Every address staging answers for a pair or an old claim, and what decides it.
          </p>
        </div>
        {gone(pages.error) && (
          <Card>
            <CardHeader>
              <CardTitle>Bundle {version} is no longer in the store</CardTitle>
              <CardDescription>
                Nothing is shown from another version.{' '}
                <Link to='/pages' search={{}} className='underline'>
                  Open the current bundle
                </Link>
              </CardDescription>
            </CardHeader>
          </Card>
        )}
        {pages.error && !gone(pages.error) && (
          <p className='text-destructive'>{String(pages.error)}</p>
        )}
        {data && (
          <div className='space-y-4'>
            <Card>
              <CardHeader>
                <CardTitle>Sources</CardTitle>
                <CardDescription>
                  Pairs and the lab's claim scope from bundle{' '}
                  <span className='font-mono'>{data.version ?? 'none'}</span>
                  {data.version && !data.current && ' (not current)'}. What each old address
                  answers from the files staging was published with.
                </CardDescription>
              </CardHeader>
              <CardContent className='grid gap-2 text-sm md:grid-cols-2'>
                <ul className='space-y-1'>
                  {data.files.map((f) => (
                    <li key={f.pathname}>
                      <span className='font-mono'>{f.pathname}</span>{' '}
                      {f.status === 200 ? (
                        <Badge variant='secondary'>read</Badge>
                      ) : (
                        <Badge variant='destructive'>{f.status ?? 'no answer'}</Badge>
                      )}
                    </li>
                  ))}
                </ul>
                <p>
                  {data.scope
                    ? `The lab's claim scope: ${number.format(data.scope.redirects)} verified redirects, ${number.format(data.scope.held)} held claims.`
                    : 'This bundle has no claim scope (PairClaimScopePage).'}
                </p>
              </CardContent>
            </Card>
            <div className='flex flex-wrap items-center gap-3'>
              <Tabs value={show} onValueChange={(v) => setSearch({ show: v === 'all' ? undefined : (v as PagesSearch['show']) })}>
                <TabsList className='flex-wrap'>
                  {FILTERS.map((f) => (
                    <TabsTrigger key={f} value={f}>
                      {LABELS[f]}
                      {f !== 'all' && ` ${number.format(data.counts[f])}`}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
              <form
                className='flex gap-2'
                onSubmit={(e) => {
                  e.preventDefault()
                  setLimit(PAGE)
                  setSearch({ q: words.trim() || undefined })
                }}
              >
                <Input
                  aria-label='Address or title'
                  placeholder='Address or title'
                  value={words}
                  onChange={(e) => setWords(e.target.value)}
                  className='w-64'
                />
                <Button type='submit' variant='outline'>
                  Find
                </Button>
              </form>
            </div>
            <div className='overflow-x-auto'>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Address</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Staging answers</TableHead>
                    <TableHead>Lab's claim scope</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.slice(0, limit).map((row) => (
                    <TableRow
                      key={row.address}
                      data-state={search.address === row.address ? 'selected' : undefined}
                    >
                      <TableCell className='font-mono text-xs'>
                        <Link
                          to='/pages'
                          search={{ ...search, address: row.address }}
                          className='underline-offset-2 hover:underline'
                        >
                          {row.address}
                        </Link>
                        {row.differs && (
                          <Badge variant='destructive' className='ms-2'>
                            differs
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className='max-w-72 truncate'>{row.title ?? '—'}</TableCell>
                      <TableCell>
                        <SiteCell row={row} />
                      </TableCell>
                      <TableCell>
                        <LabCell row={row} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className='flex items-center justify-between text-sm'>
              <span className='text-muted-foreground'>
                {number.format(Math.min(limit, rows.length))} of {number.format(rows.length)}
              </span>
              {limit < rows.length && (
                <Button variant='outline' size='sm' onClick={() => setLimit(limit + PAGE)}>
                  Show more
                </Button>
              )}
            </div>
          </div>
        )}
        <AddressSheet
          row={open}
          version={data?.version ?? version}
          address={search.address}
          onClose={() => setSearch({ address: undefined })}
        />
      </Main>
    </>
  )
}

function AddressSheet({
  row,
  version,
  address,
  onClose,
}: {
  row?: PageRow
  version?: string | null
  address?: string
  onClose: () => void
}) {
  const [asked, setAsked] = useState(false)
  useEffect(() => setAsked(false), [address])
  const check = useQuery({
    queryKey: ['check', address],
    queryFn: () => api<Check>(`/pages/check?path=${encodeURIComponent(address ?? '')}`),
    enabled: asked && !!address,
  })
  const lab = row?.lab
  return (
    <Sheet open={!!address} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className='w-full overflow-y-auto sm:max-w-xl'>
        <SheetHeader>
          <SheetTitle className='font-mono'>{address}</SheetTitle>
          <SheetDescription>{row?.title ?? (row ? row.kind : 'Not in this inventory')}</SheetDescription>
        </SheetHeader>
        <div className='space-y-4 px-4 pb-6 text-sm'>
          {row?.kind === 'pair' && (
            <dl className='grid grid-cols-[9rem_1fr] gap-x-3 gap-y-1'>
              <dt className='text-muted-foreground'>Status code</dt>
              <dd className='font-mono'>{row.status}</dd>
              <dt className='text-muted-foreground'>Trials</dt>
              <dd>{row.trials}</dd>
              <dt className='text-muted-foreground'>Page file</dt>
              <dd>
                <Link
                  to='/models/$id'
                  params={{ id: 'page:PairPage' }}
                  // The page file of the bundle this view is bound to, not the current one.
                  search={{ key: row.address.slice(1), version: version ?? undefined }}
                  className='underline'
                >
                  PairPage {row.address.slice(1)}
                </Link>
              </dd>
              {row.claim && (
                <>
                  <dt className='text-muted-foreground'>Old claim</dt>
                  <dd className='font-mono'>/{row.claim}</dd>
                </>
              )}
            </dl>
          )}
          {row?.kind === 'old claim' && (
            <>
              <section className='space-y-1'>
                <h3 className='font-medium'>Staging answers</h3>
                <SiteCell row={row} />
                {row.site?.status === 200 && (
                  <p className='text-muted-foreground'>
                    Its own page, kept as production built it
                    {row.site.searchable ? ', and found by search.' : '. Not in search.'}
                  </p>
                )}
                {row.heldFrom && (
                  <p>
                    Held by the site from <span className='font-mono'>{row.heldFrom}</span>{' '}
                    (held-redirects.json): it does not lead there.
                  </p>
                )}
              </section>
              <section className='space-y-1'>
                <h3 className='font-medium'>The lab's claim scope</h3>
                {!lab && <p className='text-muted-foreground'>Not in the lab's claim scope.</p>}
                {lab?.scope === 'verified' && (
                  <p>
                    Verified to lead to <span className='font-mono'>{lab.pair}</span>.
                  </p>
                )}
                {lab?.scope === 'held' && (
                  <p>
                    Held{lab.pair ? <> from <span className='font-mono'>{lab.pair}</span>, the pair it would lead to</> : ', with no pair to lead to'}.{' '}
                    {lab.reason && (
                      <>
                        {REASONS[lab.reason] ?? 'Reason not known to this site'}{' '}
                        <span className='font-mono text-muted-foreground'>({lab.reason})</span>.
                      </>
                    )}
                  </p>
                )}
              </section>
              {row.differs && (
                <p className='rounded-md border border-destructive p-2'>{row.differs}</p>
              )}
            </>
          )}
          <section className='space-y-2'>
            <h3 className='font-medium'>Ask staging now</h3>
            <Button variant='outline' size='sm' onClick={() => (asked ? check.refetch() : setAsked(true))}>
              Ask staging for {address}
            </Button>
            {check.data && (
              <dl className='grid grid-cols-[9rem_1fr] gap-x-3 gap-y-1'>
                <dt className='text-muted-foreground'>Status</dt>
                <dd>{check.data.status ?? `no answer: ${check.data.error}`}</dd>
                {check.data.location && (
                  <>
                    <dt className='text-muted-foreground'>Leads to</dt>
                    <dd className='font-mono'>{check.data.location}</dd>
                  </>
                )}
                <dt className='text-muted-foreground'>Type</dt>
                <dd className='font-mono'>{check.data.type ?? '—'}</dd>
                <dt className='text-muted-foreground'>Robots</dt>
                <dd className='font-mono'>{check.data.robots ?? '—'}</dd>
                <dt className='text-muted-foreground'>Cache</dt>
                <dd className='font-mono'>{check.data.cache ?? '—'}</dd>
              </dl>
            )}
            {check.error && <p className='text-destructive'>{String(check.error)}</p>}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}
