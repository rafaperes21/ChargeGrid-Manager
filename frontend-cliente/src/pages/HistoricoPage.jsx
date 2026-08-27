import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiClient } from '../lib/apiClient'
import { formatCurrency, formatDateTime, formatEnergyKwh } from '../lib/format'

const BREAKDOWN_ROWS = [
  ['gross_amount', 'Bruto'],
  ['promo_value', 'Promoção (minutos grátis)', true],
  ['discount_value', 'Desconto do plano', true],
  ['franquia_value', 'Franquia', true],
]

function Receipt({ sessionId }) {
  const { data: receipt, isLoading } = useQuery({
    queryKey: ['receipt', sessionId],
    queryFn: () => apiClient.get(`/sessions/${sessionId}/receipt`),
  })

  if (isLoading) return <p className="px-4 pb-3 text-xs text-muted">Carregando recibo…</p>
  if (!receipt) return null

  return (
    <div className="flex flex-col gap-1.5 border-t border-hairline px-4 py-3">
      {BREAKDOWN_ROWS.map(([key, label, isSubtracted]) => {
        const value = Number(receipt[key])
        if (value === 0) return null
        return (
          <div key={key} className="flex items-center justify-between text-xs text-muted-2">
            <span>{label}</span>
            <span>{isSubtracted ? '− ' : ''}{formatCurrency(value)}</span>
          </div>
        )
      })}
      <div className="mt-1 flex items-center justify-between border-t border-hairline pt-1.5 text-sm font-bold text-ink">
        <span>Total cobrado</span>
        <span>{formatCurrency(receipt.final_amount)}</span>
      </div>
    </div>
  )
}

function SessionRow({ session }) {
  const [expanded, setExpanded] = useState(false)
  const isFinished = session.status === 'finished'

  return (
    <div className="rounded-2xl border border-hairline bg-white">
      <button
        type="button"
        onClick={() => isFinished && setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <p className="text-sm font-semibold text-ink">{formatDateTime(session.started_at)}</p>
          <p className="mt-0.5 text-xs text-muted-2">
            {session.energy_kwh !== null ? formatEnergyKwh(session.energy_kwh) : '—'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isFinished ? (
            <span className="text-sm font-bold text-ink">{formatCurrency(session.amount_due)}</span>
          ) : (
            <span className="rounded-full bg-status-problema/10 px-2.5 py-1 text-[11px] font-semibold text-status-problema">
              Sem cobrança
            </span>
          )}
          {isFinished && <span className="text-muted">{expanded ? '▲' : '▼'}</span>}
        </div>
      </button>
      {expanded && isFinished && <Receipt sessionId={session.id} />}
    </div>
  )
}

export function HistoricoPage() {
  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions-mine'],
    queryFn: () => apiClient.get('/sessions/mine'),
  })

  return (
    <div className="flex flex-1 flex-col gap-3 p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">Histórico</p>

      {isLoading && <p className="text-sm text-muted">Carregando…</p>}

      {sessions?.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-hairline p-8 text-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#9A96A6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v5h5" />
            <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
            <path d="M12 7v5l4 2" />
          </svg>
          <p className="text-sm text-muted-2">Nenhuma sessão concluída ainda.</p>
        </div>
      )}

      <div className="flex flex-col gap-2.5">
        {sessions?.map((session) => (
          <SessionRow key={session.id} session={session} />
        ))}
      </div>
    </div>
  )
}
