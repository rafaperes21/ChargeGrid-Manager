import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { routes } from '../routes'

// Desktop-first: sidebar fixa, alta densidade (monitor de sala, sessão longa).
// Ver skill ui-dois-portais — o layout final vem do Figma, isto é só a estrutura.
export function AppShell() {
  const { establishment, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-48 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <p className="text-sm font-semibold text-slate-900">ChargeGrid-Manager</p>
          {establishment && <p className="mt-0.5 truncate text-xs text-slate-400">{establishment.name}</p>}
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-2">
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
        <button
          type="button"
          onClick={logout}
          className="border-t border-slate-200 px-4 py-3 text-left text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-900"
        >
          Sair
        </button>
      </aside>

      <div className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
