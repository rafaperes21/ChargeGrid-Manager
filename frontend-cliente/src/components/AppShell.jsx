import { useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { BottomNav } from './BottomNav'
import { ThemeToggle } from './ui/ThemeToggle'
import { useAuth } from '../lib/auth'
import { gsap, TRANSITION, useGSAP } from '../lib/motion'

// Mobile-first: usado em pé, no estacionamento, com pouca paciência (skill ui-dois-portais).
export function AppShell() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const outletRef = useRef(null)

  // Fade + slide leve ao trocar de pagina - reforca a troca de contexto sem chamar atencao
  // pra si mesma (skill motion-design: personalidade Corporate, sem overshoot).
  useGSAP(() => {
    if (!outletRef.current) return
    gsap.fromTo(outletRef.current, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [pathname])

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[430px] flex-col bg-surface font-body">
      <div className="flex items-center justify-between gap-2.5 bg-ink-fixed px-5 py-[18px] text-white">
        <div className="flex items-center gap-2.5">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
          </svg>
          <span className="font-heading text-[15px] font-semibold">{user?.full_name ?? 'ChargeGrid'}</span>
        </div>
        <ThemeToggle />
      </div>

      <div ref={outletRef} className="flex flex-1 flex-col overflow-y-auto">
        <Outlet />
      </div>

      <BottomNav />
    </div>
  )
}
