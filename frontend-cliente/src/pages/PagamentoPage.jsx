import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ReceiptBreakdown } from '../components/ReceiptBreakdown'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { apiClient } from '../lib/apiClient'
import { formatEnergyKwh } from '../lib/format'
import { PAYMENT_METHOD_LABELS } from '../lib/paymentMethods'

function elapsedLabel(startedAtIso, endedAtIso) {
  const totalMinutes = Math.max(
    0,
    Math.round((new Date(endedAtIso) - new Date(startedAtIso)) / 60_000)
  )
  if (totalMinutes < 60) return `${totalMinutes} min`
  const hours = Math.floor(totalMinutes / 60)
  const rest = totalMinutes % 60
  return rest === 0 ? `${hours}h` : `${hours}h${String(rest).padStart(2, '0')}`
}

// Resumo + "pagamento" pos-parada manual (Tarefa 3a). A sessao ja esta `finished` quando
// esta tela e aberta, entao `payment_method` no backend ja esta congelado - a escolha aqui
// e so local (nunca chama PATCH /sessions/current/payment-method, que devolveria 409 pra
// sessao terminal). Mesmo espirito declarativo do resto do sistema: nao processa pagamento
// de verdade, so decide o que mostrar na tela de agradecimento.
export function PagamentoPage() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const stateEstablishmentId = location.state?.establishmentId

  const { data: receipt, isLoading } = useQuery({
    queryKey: ['receipt', sessionId],
    queryFn: () => apiClient.get(`/sessions/${sessionId}/receipt`),
  })

  // Fallback pra reload direto nesta URL (sem o `state` da navegacao) - acha o
  // establishment_id pelo historico, que ja lista as sessoes finalizadas do cliente.
  const { data: sessionsMine } = useQuery({
    queryKey: ['sessions-mine'],
    queryFn: () => apiClient.get('/sessions/mine'),
    enabled: !stateEstablishmentId,
  })
  const establishmentId =
    stateEstablishmentId ?? sessionsMine?.find((item) => item.id === sessionId)?.establishment_id

  const { data: establishments } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
    enabled: Boolean(establishmentId),
  })
  const establishment = establishments?.find((item) => item.id === establishmentId)
  const acceptedMethods = establishment?.accepted_payment_methods ?? []

  const [selectedMethod, setSelectedMethod] = useState(null)
  const currentMethod = selectedMethod ?? receipt?.payment_method ?? null

  if (isLoading || !receipt) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-5">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">Resumo da sessão</p>

      <div className="flex flex-col gap-2 rounded-2xl border border-hairline p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-2">Energia carregada</span>
          <span className="font-semibold text-ink">{formatEnergyKwh(receipt.energy_kwh)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-2">Tempo de sessão</span>
          <span className="font-semibold text-ink">
            {elapsedLabel(receipt.started_at, receipt.ended_at)}
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-hairline p-4">
        <ReceiptBreakdown receipt={receipt} />
      </div>

      {acceptedMethods.length > 0 && (
        <div className="rounded-2xl border border-hairline px-4 py-3">
          <p className="text-xs text-muted-2">Forma de pagamento</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {acceptedMethods.map((method) => {
              const active = currentMethod === method
              return (
                <button
                  type="button"
                  key={method}
                  onClick={() => setSelectedMethod(method)}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                    active ? 'bg-brand text-white' : 'border border-hairline text-muted-2'
                  }`}
                >
                  {PAYMENT_METHOD_LABELS[method]}
                </button>
              )
            })}
          </div>
        </div>
      )}

      <Button
        className="mt-2 w-full"
        onClick={() =>
          navigate(`/obrigado/${sessionId}`, {
            state: { amount: receipt.final_amount, paymentMethod: currentMethod },
          })
        }
      >
        Confirmar pagamento
      </Button>
    </div>
  )
}
