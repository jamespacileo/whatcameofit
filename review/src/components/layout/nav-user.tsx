import { useQuery } from '@tanstack/react-query'
import { LogOut } from 'lucide-react'
import { api, type Me } from '@/lib/api'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

// Who Cloudflare Access signed in, as the Worker read it from the verified token. Signing
// out is Access's own address, which ends the Access session for this application.
export function NavUser() {
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me') })
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton size='lg' asChild>
          <a href='/cdn-cgi/access/logout' title='Sign out'>
            <div className='grid flex-1 text-start text-sm leading-tight'>
              <span className='truncate text-xs text-muted-foreground'>
                Signed in as
              </span>
              <span className='truncate font-semibold'>
                {me.data?.email ?? '…'}
              </span>
            </div>
            <LogOut className='ms-auto size-4' />
          </a>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
