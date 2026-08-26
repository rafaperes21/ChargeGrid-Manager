import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

// Desktop-first: sidebar fixa, alta densidade (monitor de sala, sessão longa).
export function AppShell() {
  return (
    <div className="flex min-h-screen bg-cream">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
