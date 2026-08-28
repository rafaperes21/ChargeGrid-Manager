import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { apiClient } from '../lib/apiClient'
import { formatCurrency } from '../lib/format'
import { gsap, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'
import { PAYMENT_METHOD_LABELS } from '../lib/paymentMethods'

// Fechamento da jornada (Tarefa 3b) - o valor normalmente chega via `state` da navegacao
// (Tarefa 3a), mas busca o recibo de novo se a tela for aberta direto/recarregada, pro link
// continuar valido numa demo mesmo depois de um reload.
export function ObrigadoPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const stateAmount = location.state?.amount
  const statePaymentMethod = location.state?.paymentMethod

  const { data: receipt } = useQuery({
    queryKey: ['receipt', sessionId],
    queryFn: () => apiClient.get(`/sessions/${sessionId}/receipt`),
    enabled: stateAmount == null,
  })

  const finalAmount = stateAmount ?? receipt?.final_amount
  const paymentMethod = statePaymentMethod ?? receipt?.payment_method

  const containerRef = useRef(null)
  useGSAP(() => {
    if (!containerRef.current || prefersReducedMotion()) return
    gsap.fromTo(containerRef.current, { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [])

  return (
    <div ref={containerRef} className="flex flex-1 flex-col items-center gap-6 p-6 pt-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-3xl">
        🔌
      </div>

      <div>
        <p className="text-base font-semibold text-ink">Obrigado por usar o ChargeGrid-Manager!</p>
        <p className="mt-1 text-sm text-muted-2">Sua sessão foi encerrada com sucesso.</p>
      </div>

      {finalAmount != null && (
        <div className="w-full rounded-2xl border border-hairline p-5">
          <p className="text-xs text-muted-2">Valor pago</p>
          <p className="mt-1 font-heading text-4xl font-bold leading-none text-ink">
            {formatCurrency(finalAmount)}
          </p>
          {paymentMethod && (
            <p className="mt-2 text-xs text-muted-2">
              via {PAYMENT_METHOD_LABELS[paymentMethod] ?? paymentMethod}
            </p>
          )}
        </div>
      )}

      <div className="mt-2 flex w-full flex-col gap-2">
        <Button className="w-full" onClick={() => navigate('/mapa')}>
          Voltar ao mapa
        </Button>
        <Button variant="secondary" className="w-full" onClick={() => navigate('/historico')}>
          Ver histórico completo
        </Button>
      </div>
    </div>
  )
}
