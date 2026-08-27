import { useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { gsap, TRANSITION, useGSAP } from '../lib/motion'

// Desktop-first: sidebar fixa, alta densidade (monitor de sala, sessão longa).
export function AppShell() {
  const { pathname } = useLocation()
  const outletRef = useRef(null)

  // Fade + slide leve ao trocar de pagina - reforca a troca de contexto sem chamar atencao
  // pra si mesma (skill motion-design: personalidade Corporate, sem overshoot).
  useGSAP(() => {
    if (!outletRef.current) return
    gsap.fromTo(outletRef.current, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [pathname])

  return (
    <div className="flex min-h-screen bg-cream">
      <Sidebar />
      <div ref={outletRef} className="flex flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
