import { createFileRoute } from '@tanstack/react-router'
import { ModelDetail } from '@/features/models/detail'

// The address holds everything a view of records depends on: the bundle version it is bound
// to, the page of records, and the record open in the sheet, so a link reopens the same view.
export type ModelSearch = { version?: string; offset?: number; key?: string }

export const Route = createFileRoute('/_authenticated/models/$id')({
  validateSearch: (search: Record<string, unknown>): ModelSearch => ({
    version:
      typeof search.version === 'string' && /^[a-f0-9]{16}$/.test(search.version)
        ? search.version
        : undefined,
    offset:
      Number.isInteger(Number(search.offset)) && Number(search.offset) > 0
        ? Number(search.offset)
        : undefined,
    key: typeof search.key === 'string' ? search.key : undefined,
  }),
  component: RouteComponent,
})

// eslint-disable-next-line react-refresh/only-export-components
function RouteComponent() {
  const { id } = Route.useParams()
  const search = Route.useSearch()
  return <ModelDetail key={id} id={id} search={search} />
}
