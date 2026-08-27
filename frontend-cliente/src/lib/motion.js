import { gsap } from 'gsap'
import { useGSAP } from '@gsap/react'
import { Flip } from 'gsap/Flip'

gsap.registerPlugin(useGSAP, Flip)

// Constantes compartilhadas de motion design - nenhum componente deve inventar o proprio
// tempo de animacao. Personalidade "Corporate" (skill motion-design): duracao 200-400ms,
// sem overshoot - combina com um app operacional (carregar o carro, ver fila, ver recibo).
export const MICRO = { duration: 0.3, ease: 'power2.out' } // micro-interacoes: contagem, badges, pulso
export const TRANSITION = { duration: 0.6, ease: 'power3.inOut' } // troca de tela, entrada de card

/**
 * Roda `callback(reduceMotion)` dentro de um gsap.matchMedia() escopado - reverte sozinho
 * quando o componente desmonta ou a preferencia muda. Usar para animacoes que vivem
 * enquanto o componente existe (pulso continuo, transicao de entrada de tela). `reduceMotion`
 * vem de `prefers-reduced-motion: reduce`; quem anima decide como reagir (normalmente
 * duration: 0, pulando direto pro estado final).
 */
export function withMotionPreferences(scope, callback) {
  const mm = gsap.matchMedia(scope)
  mm.add({ reduceMotion: '(prefers-reduced-motion: reduce)' }, (context) =>
    callback(context.conditions.reduceMotion)
  )
  return mm
}

/**
 * Checagem sincrona de `prefers-reduced-motion: reduce` - para animacoes disparadas por um
 * evento pontual (ex.: numero mudou, precisa contar) em vez de um contexto persistente.
 * matchMedia() (a API do GSAP) e pra configuracao que vive com o componente; aqui so
 * precisamos saber a preferencia no instante em que o disparo acontece.
 */
export function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Anima o texto de `target` (nó DOM, normalmente via ref) de `from` até `to`, formatado por
 * `formatter` a cada frame - usado pra contagem ascendente de valores (receita, valor
 * acumulado). Nunca mexe em estado do React durante a animação (escreve direto no DOM),
 * então não briga com re-render; o valor final vem sempre do dado real, nunca extrapolado.
 */
export function animateNumber(target, { from, to, duration, ease, formatter = String }) {
  if (!target) return
  // Sempre escreve o estado inicial na hora, sincrono - evita texto em branco no primeiro
  // paint e cobre o caso from === to (gsap.to() nao roda onUpdate se nao ha nada pra
  // interpolar, entao a contagem nunca dispararia sozinha).
  target.textContent = formatter(from)
  if (from === to || prefersReducedMotion()) {
    target.textContent = formatter(to)
    return
  }
  const proxy = { value: from }
  gsap.to(proxy, {
    value: to,
    duration,
    ease,
    onUpdate: () => {
      target.textContent = formatter(proxy.value)
    },
  })
}

export { Flip, gsap, useGSAP }
