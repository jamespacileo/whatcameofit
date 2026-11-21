import { LayoutDashboard } from 'lucide-react'
import { type SidebarData } from '../types'

// Later phases add Models, Pages, Search and Compare here (plan: Admin dashboard plan).
export const sidebarData: SidebarData = {
  navGroups: [
    {
      title: 'Staging',
      items: [{ title: 'Overview', url: '/', icon: LayoutDashboard }],
    },
  ],
}
