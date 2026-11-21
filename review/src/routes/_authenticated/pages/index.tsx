import { createFileRoute } from '@tanstack/react-router'
import { PagesView } from '@/features/pages'

// The address holds the view: the bundle it is bound to, the filter, the words searched for and
// the address open in the sheet, so a link reopens the same view.
export const FILTERS = ['all', 'pairs', 'kept', 'redirects', 'gone', 'held', 'differs'] as const
export type PagesSearch = {
  version?: string
  show?: (typeof FILTERS)[number]
  q?: string
  address?: string
}

export const Route = createFileRoute('/_authenticated/pages/')({
  validateSearch: (search: Record<string, unknown>): PagesSearch => ({
    version:
      typeof search.version === 'string' && /^[a-f0-9]{16}$/.test(search.version)
        ? search.version
        : undefined,
    show: FILTERS.includes(search.show as never)
      ? (search.show as PagesSearch['show'])
      : undefined,
    q: typeof search.q === 'string' && search.q ? search.q : undefined,
    address:
      typeof search.address === 'string' && search.address.startsWith('/')
        ? search.address
        : undefined,
  }),
  component: RouteComponent,
})

// eslint-disable-next-line react-refresh/only-export-components
function RouteComponent() {
  return <PagesView search={Route.useSearch()} />
}
