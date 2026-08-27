import { NavLink, useMatch } from 'react-router-dom'
import { useRef } from 'react'
import { routes } from '../routes'
import { gsap, MICRO, useGSAP } from '../lib/motion'

const ICONS = {
  '/': <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />,
  '/mapa': (
    <path d="M9 20l-5.447-2.724A1 1 0 0 1 3 16.382V5.618a1 1 0 0 1 1.447-.894L9 7m0 13 6-3m-6 3V7m6 10 4.553 2.276A1 1 0 0 0 21 18.382V7.618a1 1 0 0 0-.553-.894L15 4m0 13V4m0 0L9 7" />
  ),
  '/historico': (
    <>
      <path d="M3 3v5h5" />
      <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
      <path d="M12 7v5l4 2" />
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
  '/ajuda': <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
}

function NavItem({ route }) {
  const isActive = Boolean(useMatch({ path: route.path, end: route.path === '/' }))
  const indicatorRef = useRef(null)
  const iconRef = useRef(null)

  // Destaque do item ativo transiciona suavemente (barra + cor do icone) em vez de trocar
  // de classe instantaneo.
  useGSAP(() => {
    if (!indicatorRef.current) return
    gsap.to(indicatorRef.current, { scaleX: isActive ? 1 : 0, ...MICRO })
    gsap.to(iconRef.current, { stroke: isActive ? '#E60012' : '#9A96A6', ...MICRO })
  }, [isActive])

  return (
    <NavLink
      to={route.path}
      end={route.path === '/'}
      className="relative flex flex-1 flex-col items-center gap-1 py-2.5"
    >
      <span
        ref={indicatorRef}
        className="absolute top-0 left-1/2 h-[3px] w-[22px] origin-center -translate-x-1/2 rounded-b"
        style={{ background: 'linear-gradient(90deg,#E60012,#FF7A1A)', transform: 'scaleX(0)' }}
      />
      <svg
        ref={iconRef}
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#9A96A6"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {ICONS[route.path]}
      </svg>
      <span className={`text-[10px] font-semibold transition-colors duration-300 ${isActive ? 'text-brand' : 'text-muted-3'}`}>
        {route.title}
      </span>
    </NavLink>
  )
}

export function BottomNav() {
  return (
    <div className="flex w-full border-t border-hairline bg-white font-body">
      {routes.map((route) => (
        <NavItem key={route.path} route={route} />
      ))}
    </div>
  )
}
