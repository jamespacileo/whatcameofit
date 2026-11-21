import { useQuery } from '@tanstack/react-query'
import { api, type Overview as OverviewData } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
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

const number = new Intl.NumberFormat('en-GB')

// The staging store at a glance: which bundle version readers get, what it holds, and how
// many rows each pair table keeps across the versions still loaded.
export function Overview() {
  const overview = useQuery({
    queryKey: ['overview', 'staging'],
    queryFn: () => api<OverviewData>('/staging/overview'),
  })
  const data = overview.data
  return (
    <>
      <Header>
        <Search className='me-auto' />
        <ThemeSwitch />
        <ConfigDrawer />
      </Header>
      <Main>
        <div className='mb-4 space-y-1'>
          <h1 className='text-2xl font-bold tracking-tight'>Staging</h1>
          <p className='text-muted-foreground'>
            What staging.whatcameofit.com reads from its store, read-only.
          </p>
        </div>
        {overview.isError && (
          <p className='text-destructive'>{String(overview.error)}</p>
        )}
        {data && !data.current && (
          <p className='text-muted-foreground'>
            This store has no current bundle of pairs.
          </p>
        )}
        {data?.current && (
          <div className='space-y-4'>
            <Card>
              <CardHeader>
                <CardTitle className='font-mono text-base'>
                  {data.current.version}
                </CardTitle>
                <CardDescription>
                  Current bundle, loaded {data.current.loaded_at}. Rows in this version, by table:
                </CardDescription>
              </CardHeader>
              <CardContent className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                {Object.entries(data.current.counts).map(([table, count]) => (
                  <div key={table}>
                    <div className='text-2xl font-bold'>
                      {number.format(count)}
                    </div>
                    <div className='font-mono text-sm text-muted-foreground'>
                      {table}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
            <div className='grid gap-4 lg:grid-cols-2'>
              <Card>
                <CardHeader>
                  <CardTitle>Loaded versions</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Version</TableHead>
                        <TableHead>Loaded</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.versions.map((v) => (
                        <TableRow key={v.version}>
                          <TableCell className='font-mono'>
                            {v.version}{' '}
                            {v.current && <Badge variant='secondary'>current</Badge>}
                          </TableCell>
                          <TableCell>{v.loaded_at}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Tables</CardTitle>
                  <CardDescription>Rows across loaded versions</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableBody>
                      {data.tables.map((t) => (
                        <TableRow key={t.name}>
                          <TableCell className='font-mono'>{t.name}</TableCell>
                          <TableCell className='text-end'>
                            {t.rows === null ? 'not in this store' : number.format(t.rows)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </Main>
    </>
  )
}
