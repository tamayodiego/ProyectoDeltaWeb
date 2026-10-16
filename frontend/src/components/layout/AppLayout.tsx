import { Outlet } from 'react-router'

import { AppHeader } from './AppHeader'

export function AppLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <AppHeader />
      <Outlet />
    </div>
  )
}
