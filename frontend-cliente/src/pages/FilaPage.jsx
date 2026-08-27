import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ApiError, apiClient } from '../lib/apiClient'

const RESERVATION_WINDOW_MINUTES = 15

function reservationSecondsLeft(reservedAtIso) {
  const reservedAt = new Date(reservedAtIso).getTime()
  const deadline = reservedAt + RESERVATION_WINDOW_MINUTES * 60 * 1000
  return Math.max(0, Math.floor((deadline - Date.now()) / 1000))
}

function formatCountdown(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function NotInQueue() {
  return (
    <div className="flex flex-1 flex-col items-center gap-5 px-5 pb-5 pt-9">
      <div className="relative h-[160px] w-[160px]">
        <svg width="160" height="160" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="76" fill="none" stroke="#EAE6F2" strokeWidth="14" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-2">Posição</span>
          <span className="text-4xl font-extrabold text-muted-3">—</span>
        </div>
      </div>

      <p className="text-center text-sm text-muted-2">
        Você não está na fila de nenhum estacionamento no momento.
      </p>
    </div>
  )
}

export function FilaPage() {
  const { data: entry, error, isLoading } = useQuery({
    queryKey: ['queue-mine'],
    queryFn: () => apiClient.get('/queue/mine'),
    retry: false,
    refetchInterval: 10_000,
  })

  const [, forceTick] = useState(0)
  useEffect(() => {
    if (!entry?.reserved_at) return undefined
    const interval = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(interval)
  }, [entry?.reserved_at])

  if (isLoading) {
    return <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">Carregando…</div>
  }

  if ((error instanceof ApiError && error.status === 404) || !entry) {
    return <NotInQueue />
  }

  const isReserved = Boolean(entry.reserved_at)
  const secondsLeft = isReserved ? reservationSecondsLeft(entry.reserved_at) : null

  return (
    <div className="flex flex-1 flex-col items-center gap-5 px-5 pb-5 pt-9">
      <div className="relative h-[160px] w-[160px]">
        <svg width="160" height="160" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="76" fill="none" stroke="#EAE6F2" strokeWidth="14" />
          {isReserved && (
            <circle
              cx="90"
              cy="90"
              r="76"
              fill="none"
              stroke="#D97706"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 76}
              strokeDashoffset={2 * Math.PI * 76 * (1 - secondsLeft / (RESERVATION_WINDOW_MINUTES * 60))}
              transform="rotate(-90 90 90)"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-2">Posição</span>
          <span className="text-4xl font-extrabold text-ink">{entry.position}</span>
        </div>
      </div>

      {isReserved ? (
        <div className="w-full rounded-2xl border border-status-reservado bg-amber-50 px-4 py-3 text-center">
          <p className="text-sm font-semibold text-amber-900">Vaga reservada para você</p>
          <p className="mt-1 text-xs text-amber-800">
            Chegue em até {formatCountdown(secondsLeft)} min ou a reserva expira.
          </p>
        </div>
      ) : (
        <p className="text-center text-sm text-muted-2">
          Aguarde — você será notificado quando uma vaga liberar para você.
        </p>
      )}
    </div>
  )
}
