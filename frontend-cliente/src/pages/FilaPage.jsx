import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import emptyFilaIllustration from '../assets/empty-fila.svg'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { ApiError, apiClient } from '../lib/apiClient'
import { animateNumber, gsap, MICRO, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'
import { startSessionErrorMessage } from '../lib/sessionErrors'

const formatPosition = (value) => String(Math.round(value))

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
  const containerRef = useRef(null)

  useGSAP(() => {
    if (!containerRef.current || prefersReducedMotion()) return
    gsap.fromTo(containerRef.current, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [])

  return (
    <div ref={containerRef} className="flex flex-1 flex-col items-center gap-4 px-5 pb-5 pt-9 text-center">
      <img src={emptyFilaIllustration} alt="" width={120} height={120} />
      <p className="text-sm text-muted-2">Você não está na fila de nenhum estacionamento no momento.</p>
    </div>
  )
}

export function FilaPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: entry, error, isLoading } = useQuery({
    queryKey: ['queue-mine'],
    queryFn: () => apiClient.get('/queue/mine'),
    retry: false,
    refetchInterval: 10_000,
  })

  // Sair da fila (pedido explicito do usuario, 28/08/2026) - antes nao tinha jeito
  // nenhum de cancelar, ficava "rodando pra sempre" ate expirar por conta propria.
  const leaveMutation = useMutation({
    mutationFn: () => apiClient.delete('/queue/mine'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue-mine'] }),
  })

  // "Cheguei" (pedido explicito do usuario) - a vaga reservada ja tem `reserved_charger_id`
  // no /queue/mine, so faltava um jeito de confirmar a chegada na hora em vez do cliente
  // precisar ir ate o mapa achar o carregador certo sozinho. Mesmo POST /sessions/start
  // que o mapa usa - `consume_reservation` (services/queue.py) tira da fila sozinho.
  const arrivedMutation = useMutation({
    mutationFn: () => apiClient.post('/sessions/start', { charger_id: entry.reserved_charger_id }),
    onSuccess: () => navigate('/'),
  })

  const [, forceTick] = useState(0)
  useEffect(() => {
    if (!entry?.reserved_at) return undefined
    const interval = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(interval)
  }, [entry?.reserved_at])

  const positionRef = useRef(null)
  const prevPositionRef = useRef(null)

  // Transicao suave ao mudar de posicao na fila - conta do valor anterior ate o novo em vez
  // de saltar pro numero novo.
  useGSAP(() => {
    if (!entry || !positionRef.current) return
    const to = entry.position
    const from = prevPositionRef.current ?? to
    animateNumber(positionRef.current, { from, to, ...MICRO, formatter: formatPosition })
    prevPositionRef.current = to
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry?.position])

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center gap-5 px-5 pb-5 pt-9">
        <Skeleton className="h-[160px] w-[160px] rounded-full" />
        <Skeleton className="h-4 w-56" />
      </div>
    )
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
          <span ref={positionRef} className="text-4xl font-extrabold text-ink" />
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

      {isReserved && (
        <Button
          className="w-full"
          disabled={arrivedMutation.isPending}
          onClick={() => arrivedMutation.mutate()}
        >
          {arrivedMutation.isPending ? 'Iniciando…' : '📶 Cheguei — simular cartão RFID'}
        </Button>
      )}
      {arrivedMutation.isError && (
        <p className="text-xs text-status-problema">{startSessionErrorMessage(arrivedMutation.error)}</p>
      )}

      <Button
        variant="secondary"
        className="w-full"
        disabled={leaveMutation.isPending}
        onClick={() => leaveMutation.mutate()}
      >
        {leaveMutation.isPending ? 'Saindo…' : 'Cancelar e sair da fila'}
      </Button>
      {leaveMutation.isError && (
        <p className="text-xs text-status-problema">Não foi possível sair da fila agora. Tente de novo.</p>
      )}
    </div>
  )
}
