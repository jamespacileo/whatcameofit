import { Database, LayoutDashboard } from 'lucide-react'
import { type SidebarData } from '../types'

// Later phases add Pages, Search and Compare here (plan: Admin dashboard plan).
export const sidebarData: SidebarData = {
  navGroups: [
    {
      title: 'Staging',
      items: [
        { title: 'Overview', url: '/', icon: LayoutDashboard },
        { title: 'Models', url: '/models', icon: Database },
      ],
    },
  ],
}
