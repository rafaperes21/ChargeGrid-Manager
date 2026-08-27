import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ApiError, apiClient } from '../lib/apiClient'
import { formatCurrency, formatEnergyKwh } from '../lib/format'

const STATUS_LABEL = {
  pending: 'Aguardando carregador',
  active: 'Carregando',
}

function formatElapsed(startedAtIso) {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - new Date(startedAtIso).getTime()) / 1000))
  const minutes = Math.floor(elapsedSeconds / 60)
  const seconds = elapsedSeconds % 60
  return `${minutes}min ${String(seconds).padStart(2, '0')}s`
}

function NoActiveSession() {
  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-muted-3/10 px-3 py-1.5 text-xs font-medium text-muted-2">
          Nenhuma sessão ativa
        </span>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-2">Valor acumulado</p>
        <p className="mt-1 font-heading text-5xl font-bold leading-none text-muted-3">R$ —</p>
      </div>

      <div className="rounded-2xl border border-hairline bg-emerald-50 px-4 py-3">
        <p className="text-xs text-emerald-800">
          Aproxime seu cartão RFID de um carregador livre para iniciar uma sessão.
        </p>
      </div>
    </div>
  )
}

export function SessaoPage() {
  const { data: session, error, isLoading } = useQuery({
    queryKey: ['current-session'],
    queryFn: () => apiClient.get('/sessions/current'),
    retry: false,
    refetchInterval: 15_000,
  })

  const [, forceTick] = useState(0)
  useEffect(() => {
    if (session?.status !== 'active' && session?.status !== 'pending') return undefined
    const interval = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(interval)
  }, [session?.status])

  if (isLoading) {
    return <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">Carregando…</div>
  }

  if (error instanceof ApiError && error.status === 404) {
    return <NoActiveSession />
  }

  if (!session) {
    return <NoActiveSession />
  }

  const isActive = session.status === 'active'
  const hasTariff = session.estimated_amount_due !== null && session.estimated_amount_due !== undefined

  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-status-carregando/10 px-3 py-1.5 text-xs font-medium text-status-carregando">
          <span className="cgm-pulse inline-block h-1.5 w-1.5 rounded-full bg-status-carregando" />
          {STATUS_LABEL[session.status] ?? session.status}
        </span>
        <span className="font-mono text-xs text-muted-2">{formatElapsed(session.started_at)}</span>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-2">
          Valor acumulado {isActive && '(estimado)'}
        </p>
        <p className="mt-1 font-heading text-5xl font-bold leading-none text-ink">
          {isActive && hasTariff ? formatCurrency(session.estimated_amount_due) : 'R$ —'}
        </p>
        {isActive && !hasTariff && (
          <p className="mt-1 text-xs text-status-problema">
            Sem tarifa configurada para este horário — valor final pode ficar indisponível.
          </p>
        )}
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-hairline px-4 py-3">
        <span className="text-xs text-muted-2">Energia carregada</span>
        <span className="text-sm font-semibold text-ink">
          {session.energy_kwh !== null ? formatEnergyKwh(session.energy_kwh) : '—'}
        </span>
      </div>

      {session.status === 'pending' && (
        <div className="rounded-2xl border border-hairline bg-amber-50 px-4 py-3">
          <p className="text-xs text-amber-800">
            Cartão reconhecido — aguardando o carregador começar a fornecer energia.
          </p>
        </div>
      )}
    </div>
  )
}
