import { Database, FileText, LayoutDashboard } from 'lucide-react'
import { type SidebarData } from '../types'

// Later phases add Search and Compare here (plan: Admin dashboard plan).
export const sidebarData: SidebarData = {
  navGroups: [
    {
      title: 'Staging',
      items: [
        { title: 'Overview', url: '/', icon: LayoutDashboard },
        { title: 'Models', url: '/models', icon: Database },
        { title: 'Pages', url: '/pages', icon: FileText },
      ],
    },
  ],
}
