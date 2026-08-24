import { NavLink, Outlet } from 'react-router-dom'
import { routes } from '../routes'

// Desktop-first: sidebar fixa, alta densidade (monitor de sala, sessão longa).
// Ver skill ui-dois-portais — o layout final vem do Figma, isto é só a estrutura.
export function AppShell() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-48 shrink-0 border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <p className="text-sm font-semibold text-slate-900">ChargeGrid-Manager</p>
        </div>
        <nav className="flex flex-col gap-1 p-2">
          {routes.map((route) => (
            <NavLink
              key={route.path}
              to={route.path}
              end={route.path === '/'}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`
              }
            >
              {route.title}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
