import { NavLink } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { routes } from '../routes'

// Icones por rota - mesmos paths SVG do modelo de design (feather icons).
const ICONS = {
  '/': (
    <>
      <rect x="3" y="3" width="7" height="9" />
      <rect x="14" y="3" width="7" height="5" />
      <rect x="14" y="12" width="7" height="9" />
      <rect x="3" y="16" width="7" height="5" />
    </>
  ),
  '/tarifas': (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 7v5l3 3" />
    </>
  ),
  '/usuarios-planos': (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  '/fila': (
    <>
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </>
  ),
  '/relatorios': (
    <>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </>
  ),
  '/onboarding': (
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </>
  ),
  '/assistente': <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
}

function NavIcon({ path, active }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke={active ? '#ffffff' : 'rgba(255,255,255,0.6)'}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICONS[path]}
    </svg>
  )
}

export function Sidebar() {
  const { user, establishment, logout } = useAuth()
  const mainRoutes = routes.filter((route) => route.path !== '/assistente')
  const assistantRoute = routes.find((route) => route.path === '/assistente')

  return (
    <aside className="relative flex w-[220px] shrink-0 flex-col bg-ink font-body text-white">
      <div
        className="cgm-flow pointer-events-none absolute inset-y-0 right-0 w-0.5 opacity-70"
        style={{
          background: 'linear-gradient(180deg,#E60012,#FF7A1A,#7C3AED,#E60012)',
          backgroundSize: '100% 300%',
          animation: 'cgm-flow 9s linear infinite',
        }}
      />

      <div className="flex items-center gap-2.5 border-b border-white/10 px-5 py-[22px]">
        <svg width="30" height="30" viewBox="0 0 24 24" className="shrink-0">
          <defs>
            <linearGradient id="boltGrad" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FF7A1A" />
              <stop offset="55%" stopColor="#E60012" />
              <stop offset="100%" stopColor="#7C3AED" />
            </linearGradient>
          </defs>
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" fill="url(#boltGrad)" />
        </svg>
        <p className="font-heading text-[15px] font-bold tracking-tight">ChargeGrid</p>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {mainRoutes.map((route) => (
          <NavLink
            key={route.path}
            to={route.path}
            end={route.path === '/'}
            className={({ isActive }) =>
              `relative flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-[13px] font-medium ${
                isActive
                  ? 'bg-gradient-to-r from-brand/20 to-accent-purple/15 font-semibold text-white'
                  : 'text-white/60 hover:bg-white/5'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span
                    className="absolute inset-y-1.5 -left-3 w-[3px] rounded"
                    style={{ background: 'linear-gradient(180deg,#E60012,#7C3AED)' }}
                  />
                )}
                <NavIcon path={route.path} active={isActive} />
                {route.title}
              </>
            )}
          </NavLink>
        ))}

        {assistantRoute && (
          <div className="mt-2.5 border-t border-white/10 pt-3">
            <NavLink
              to={assistantRoute.path}
              className={({ isActive }) =>
                `relative flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-[13px] font-medium ${
                  isActive
                    ? 'bg-gradient-to-r from-brand/20 to-accent-purple/15 font-semibold text-white'
                    : 'text-white/60 hover:bg-white/5'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span
                      className="absolute inset-y-1.5 -left-3 w-[3px] rounded"
                      style={{ background: 'linear-gradient(180deg,#E60012,#7C3AED)' }}
                    />
                  )}
                  <NavIcon path={assistantRoute.path} active={isActive} />
                  {assistantRoute.title}
                </>
              )}
            </NavLink>
          </div>
        )}
      </nav>

      <button
        type="button"
        onClick={logout}
        className="flex items-center gap-2.5 border-t border-white/10 px-5 py-4 text-left hover:bg-white/5"
      >
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-heading text-xs font-bold"
          style={{ background: 'linear-gradient(135deg,#E60012,#7C3AED)' }}
        >
          {(user?.full_name ?? '?').charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold">{user?.full_name ?? 'Sair'}</p>
          {establishment && <p className="truncate text-[10px] text-white/50">{establishment.name}</p>}
        </div>
      </button>
    </aside>
  )
}
