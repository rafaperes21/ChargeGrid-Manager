import { useRef } from 'react'
import { gsap, prefersReducedMotion, useGSAP } from '../../lib/motion'

// Retângulo de skeleton screen reutilizável (Tarefa I.2) - dimensiona via `className` (w-*/h-*)
// pra aproximar o tamanho do conteúdo real que vai substituir. Pulso de opacidade contínuo via
// GSAP, igual ao alerta de 90% do dashboard (Prioridade 1) - para sozinho se
// `prefers-reduced-motion: reduce` estiver ativo, ficando parado num tom intermediário.
export function Skeleton({ className = '', style }) {
  const ref = useRef(null)

  useGSAP(() => {
    if (!ref.current) return
    if (prefersReducedMotion()) {
      gsap.set(ref.current, { opacity: 0.7 })
      return
    }
    const tween = gsap.to(ref.current, {
      opacity: 0.45,
      duration: 0.8,
      ease: 'sine.inOut',
      repeat: -1,
      yoyo: true,
    })
    return () => tween.kill()
  }, [])

  return <div ref={ref} aria-hidden="true" className={`rounded-xl bg-hairline ${className}`} style={style} />
}
