import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { api, type Inventory } from '@/lib/api'
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
import { StateCell } from './state'

// Every model the site can reach, by area, with its state in each environment. A versioned
// table counts the rows of the current bundle, then all rows across loaded versions.
export function Models() {
  const inventory = useQuery({
    queryKey: ['models'],
    queryFn: () => api<Inventory>('/models'),
  })
  const data = inventory.data
  return (
    <>
      <Header>
        <Search className='me-auto' />
        <ThemeSwitch />
        <ConfigDrawer />
      </Header>
      <Main>
        <div className='mb-4 space-y-1'>
          <h1 className='text-2xl font-bold tracking-tight'>Models</h1>
          <p className='text-muted-foreground'>
            Every table the store's migrations make and every page model of the
            lab's bundle, in each environment.
          </p>
        </div>
        {inventory.isError && (
          <p className='text-destructive'>{String(inventory.error)}</p>
        )}
        {data && (
          <div className='space-y-4'>
            <div className='grid gap-4 md:grid-cols-2'>
              {data.environments.map((e) => (
                <Card key={e.name}>
                  <CardHeader>
                    <CardTitle>{e.label}</CardTitle>
                    <CardDescription>
                      {e.store}.{' '}
                      {e.readable
                        ? e.bundle
                          ? `Current bundle ${e.bundle.version}, loaded ${e.bundle.loaded_at}.`
                          : 'No current bundle.'
                        : e.reason}
                    </CardDescription>
                  </CardHeader>
                  {!!e.unlisted?.length && (
                    <CardContent className='text-sm'>
                      Tables in this store the catalogue does not list:{' '}
                      <span className='font-mono'>{e.unlisted.join(', ')}</span>
                    </CardContent>
                  )}
                  {!!e.unlistedPages?.length && (
                    <CardContent className='text-sm'>
                      Page models in the current bundle the catalogue does not list:{' '}
                      <span className='font-mono'>{e.unlistedPages.join(', ')}</span>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
            {data.areas.map((area) => (
              <Card key={area}>
                <CardHeader>
                  <CardTitle>{area}</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Model</TableHead>
                        {data.environments.map((e) => (
                          <TableHead key={e.name} className='text-end'>
                            {e.label}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.models
                        .filter((m) => m.area === area)
                        .map((m) => (
                          <TableRow key={m.id}>
                            <TableCell>
                              <Link
                                to='/models/$id'
                                params={{ id: m.id }}
                                className='font-medium hover:underline'
                              >
                                {m.name}
                              </Link>
                            </TableCell>
                            {data.environments.map((e) => (
                              <TableCell key={e.name} className='text-end'>
                                <StateCell state={m.environments[e.name]} />
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </Main>
    </>
  )
}
