import { useRef } from 'react'
import { gsap, prefersReducedMotion, useGSAP } from '../../lib/motion'

// Retangulo de skeleton screen reutilizavel - dimensiona via `className` (w-*/h-*) pra
// aproximar o tamanho do conteudo real que vai substituir. Pulso de opacidade continuo via
// GSAP (mesmo padrao do alerta de 90% do dashboard), para sozinho em
// `prefers-reduced-motion: reduce`. Espelha frontend-cliente/src/components/ui/Skeleton.jsx.
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
