import { createFileRoute } from '@tanstack/react-router'
import { ModelDetail } from '@/features/models/detail'

export const Route = createFileRoute('/_authenticated/models/$id')({
  component: RouteComponent,
})

// eslint-disable-next-line react-refresh/only-export-components
function RouteComponent() {
  const { id } = Route.useParams()
  return <ModelDetail key={id} id={id} />
}
