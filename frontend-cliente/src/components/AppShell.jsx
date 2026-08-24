import { NavLink, Outlet } from 'react-router-dom'
import { routes } from '../routes'

// Mobile-first: container estreito, nav de abas embaixo (uso em pé, no estacionamento).
// Ver skill ui-dois-portais — o layout final vem do Figma, isto é só a estrutura.
export function AppShell() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col bg-white">
      <header className="border-b border-slate-200 p-4">
        <p className="text-sm font-semibold text-slate-900">ChargeGrid-Manager</p>
      </header>

      <main className="flex flex-1 flex-col">
        <Outlet />
      </main>

      <nav className="flex border-t border-slate-200">
        {routes.map((route) => (
          <NavLink
            key={route.path}
            to={route.path}
            end={route.path === '/'}
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-xs ${isActive ? 'font-semibold text-slate-900' : 'text-slate-400'}`
            }
          >
            {route.title}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
