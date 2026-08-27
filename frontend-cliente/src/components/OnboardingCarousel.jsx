import { useRef, useState } from 'react'
import onboarding1 from '../assets/onboarding-1.svg'
import onboarding2 from '../assets/onboarding-2.svg'
import onboarding3 from '../assets/onboarding-3.svg'
import { gsap, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'
import { Button } from './ui/Button'

// 3 passos do carrossel de boas-vindas (Tarefa I.4) - mostrado uma vez no primeiro login,
// texto exatamente como pedido no briefing.
const STEPS = [
  {
    image: onboarding1,
    title: 'Encontre o eletroposto mais perto',
    body: 'Veja o mapa com distância, vagas livres e reserva antecipada.',
  },
  {
    image: onboarding2,
    title: 'Carregue e acompanhe em tempo real',
    body: 'Aproxime seu cartão RFID e acompanhe o valor e a energia consumida ao vivo.',
  },
  {
    image: onboarding3,
    title: 'Pague na hora que preferir',
    body: 'Escolha a forma de pagamento aceita pelo estabelecimento ao final da sessão.',
  },
]

export function OnboardingCarousel({ onFinish }) {
  const [stepIndex, setStepIndex] = useState(0)
  const contentRef = useRef(null)
  const step = STEPS[stepIndex]
  const isLast = stepIndex === STEPS.length - 1

  // Transicao entre passos reaproveita a mesma constante TRANSITION do resto do produto
  // (motion.js) - nenhum wizard deveria inventar o proprio tempo de animacao.
  useGSAP(() => {
    if (!contentRef.current || prefersReducedMotion()) return
    gsap.fromTo(contentRef.current, { autoAlpha: 0, x: 16 }, { autoAlpha: 1, x: 0, ...TRANSITION })
  }, [stepIndex])

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[430px] flex-col bg-surface p-6 font-body">
      <div className="flex justify-end">
        <button type="button" onClick={onFinish} className="text-xs font-semibold text-muted-2">
          Pular
        </button>
      </div>

      <div ref={contentRef} className="flex flex-1 flex-col items-center justify-center gap-5 text-center">
        <img src={step.image} alt="" width={240} height={240} />
        <h1 className="font-heading text-xl font-bold text-ink">{step.title}</h1>
        <p className="max-w-[280px] text-sm text-muted-2">{step.body}</p>
      </div>

      <div className="flex flex-col items-center gap-4 pb-4">
        <div className="flex gap-1.5">
          {STEPS.map((_, index) => (
            <span
              key={index}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                index === stepIndex ? 'w-6 bg-brand' : 'w-1.5 bg-hairline'
              }`}
            />
          ))}
        </div>
        <Button className="w-full" onClick={() => (isLast ? onFinish() : setStepIndex((i) => i + 1))}>
          {isLast ? 'Começar' : 'Próximo'}
        </Button>
      </div>
    </div>
  )
}
