import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { ApiError, apiClient } from '../lib/apiClient'
import { formatCurrency, formatEnergyKwh } from '../lib/format'
import { animateNumber, gsap, MICRO, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'
import emptySessaoIllustration from '../assets/empty-sessao.svg'

const STATUS_LABEL = {
  pending: 'Aguardando carregador',
  active: 'Carregando',
}

const PAYMENT_METHOD_LABELS = {
  pix: 'Pix',
  cartao_credito: 'Crédito',
  cartao_debito: 'Débito',
  carteira_do_app: 'Carteira do app',
}

// Declarativo (M3, Tarefa 4.3): so registra a escolha do cliente, nunca processa pagamento
// de verdade. Opcoes vem do que o estabelecimento aceita (Tarefa 4.2) - nunca inventadas.
function PaymentMethodPicker({ establishmentId, currentMethod }) {
  const queryClient = useQueryClient()

  const { data: establishments } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
  })
  const establishment = establishments?.find((item) => item.id === establishmentId)
  const acceptedMethods = establishment?.accepted_payment_methods ?? []

  const mutation = useMutation({
    mutationFn: (payment_method) =>
      apiClient.patch('/sessions/current/payment-method', { payment_method }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['current-session'] }),
  })

  if (acceptedMethods.length === 0) return null

  return (
    <div className="rounded-2xl border border-hairline px-4 py-3">
      <p className="text-xs text-muted-2">Forma de pagamento</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {acceptedMethods.map((method) => {
          const active = (currentMethod ?? mutation.variables) === method
          return (
            <button
              type="button"
              key={method}
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(method)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${
                active ? 'bg-brand text-white' : 'border border-hairline text-muted-2'
              }`}
            >
              {PAYMENT_METHOD_LABELS[method]}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Ordem real do calculo (skill tarifacao-e-sessoes): bruto -> promocao -> desconto -> franquia
// -> total. So exibe as linhas com valor diferente de zero - franquia/promocao/desconto zerados
// nao aparecem, pra nao sugerir um beneficio que nao existiu nesta sessao.
const RECEIPT_ROWS = [
  ['gross_amount', 'Bruto', false],
  ['promo_value', 'Promoção (minutos grátis)', true],
  ['discount_value', 'Desconto do plano', true],
  ['franquia_value', 'Franquia', true],
]

function formatElapsed(startedAtIso) {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - new Date(startedAtIso).getTime()) / 1000))
  const minutes = Math.floor(elapsedSeconds / 60)
  const seconds = elapsedSeconds % 60
  return `${minutes}min ${String(seconds).padStart(2, '0')}s`
}

function NoActiveSession() {
  const containerRef = useRef(null)

  useGSAP(() => {
    if (!containerRef.current || prefersReducedMotion()) return
    gsap.fromTo(containerRef.current, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [])

  return (
    <div ref={containerRef} className="flex flex-1 flex-col items-center gap-4 px-5 pb-5 pt-9 text-center">
      <img src={emptySessaoIllustration} alt="" width={120} height={120} />
      <p className="text-sm font-semibold text-ink">Nenhuma sessão ativa</p>
      <div className="w-full rounded-2xl border border-hairline bg-emerald-50 px-4 py-3">
        <p className="text-xs text-emerald-800">
          Aproxime seu cartão RFID de um carregador livre para iniciar uma sessão.
        </p>
      </div>
    </div>
  )
}

// Peca de maior valor da confirmacao: reforca "nunca cobra sem mostrar o porque" - o icone
// de confirmacao fecha primeiro, depois cada linha do calculo empilha na ordem real, uma de
// cada vez, terminando no total. Nada aqui e inventado: todo numero vem do recibo real
// (GET /sessions/{id}/receipt), que ja decompoe bruto/promocao/desconto/franquia/total.
function SessionClosedConfirmation({ receipt, onDismiss }) {
  const circleRef = useRef(null)
  const checkRef = useRef(null)
  const rowsContainerRef = useRef(null)

  const rows = RECEIPT_ROWS.filter(([key]) => Number(receipt[key]) !== 0)

  useGSAP(() => {
    const rowEls = rowsContainerRef.current?.querySelectorAll('[data-receipt-row]') ?? []

    if (prefersReducedMotion()) {
      gsap.set([circleRef.current, checkRef.current], { strokeDashoffset: 0 })
      gsap.set(rowEls, { autoAlpha: 1, y: 0 })
      return
    }

    gsap.set([circleRef.current, checkRef.current], { strokeDashoffset: 1 })
    gsap.set(rowEls, { autoAlpha: 0, y: 10 })

    const tl = gsap.timeline()
    tl.to(circleRef.current, { strokeDashoffset: 0, duration: 0.5, ease: 'power2.out' })
    tl.to(checkRef.current, { strokeDashoffset: 0, duration: 0.3, ease: 'power2.out' }, '-=0.1')
    tl.to(rowEls, { autoAlpha: 1, y: 0, stagger: 0.2, ...TRANSITION }, '+=0.15')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [receipt.session_id])

  return (
    <div className="flex flex-1 flex-col items-center gap-6 p-6 text-center">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle
          ref={circleRef}
          cx="36"
          cy="36"
          r="30"
          fill="none"
          stroke="#16a34a"
          strokeWidth="4"
          strokeLinecap="round"
          pathLength="1"
          style={{ strokeDasharray: 1 }}
          transform="rotate(-90 36 36)"
        />
        <path
          ref={checkRef}
          d="M22 37 L32 47 L50 27"
          fill="none"
          stroke="#16a34a"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength="1"
          style={{ strokeDasharray: 1 }}
        />
      </svg>

      <div>
        <p className="text-sm font-semibold text-emerald-800">Sessão encerrada</p>
        <p className="mt-1 text-xs text-muted-2">Aqui está exatamente como chegamos no valor final.</p>
      </div>

      <div ref={rowsContainerRef} className="flex w-full max-w-xs flex-col gap-2">
        {rows.map(([key, label, isSubtracted]) => (
          <div key={key} data-receipt-row className="flex items-center justify-between text-sm text-muted-2">
            <span>{label}</span>
            <span>
              {isSubtracted ? '− ' : ''}
              {formatCurrency(receipt[key])}
            </span>
          </div>
        ))}
        <div
          data-receipt-row
          className="mt-1 flex items-center justify-between border-t border-hairline pt-2 text-base font-bold text-ink"
        >
          <span>Total cobrado</span>
          <span>{formatCurrency(receipt.final_amount)}</span>
        </div>
        {receipt.payment_method && (
          <div data-receipt-row className="flex items-center justify-between text-xs text-muted-2">
            <span>Forma de pagamento</span>
            <span className="font-semibold text-ink-soft">
              {PAYMENT_METHOD_LABELS[receipt.payment_method] ?? receipt.payment_method}
            </span>
          </div>
        )}
      </div>

      <Button onClick={onDismiss}>Concluir</Button>
    </div>
  )
}

export function SessaoPage() {
  const queryClient = useQueryClient()
  const { data: session, error, isLoading } = useQuery({
    queryKey: ['current-session'],
    queryFn: () => apiClient.get('/sessions/current'),
    retry: false,
    refetchInterval: 15_000,
  })

  // sessionStorage (nao localStorage - so dura a aba atual) pra sobreviver a um reload logo
  // depois da sessao fechar: o caso comum e o celular estar com a tela apagada ou o app em
  // segundo plano exatamente quando o carregamento termina.
  const LAST_ACTIVE_KEY = 'cgm_last_active_session_id'
  const lastSessionIdRef = useRef(sessionStorage.getItem(LAST_ACTIVE_KEY))
  const [closedReceipt, setClosedReceipt] = useState(null)
  const [dismissedSessionId, setDismissedSessionId] = useState(null)

  useEffect(() => {
    if (session?.status === 'active' || session?.status === 'pending') {
      lastSessionIdRef.current = session.id
      sessionStorage.setItem(LAST_ACTIVE_KEY, session.id)
    }
  }, [session])

  // `GET /sessions/current` so devolve pending/active ou 404 (nunca um status terminal -
  // ver `api/sessions.read_current_session`) - um 404 com um id lembrado de antes e o sinal
  // de que a sessao acabou de fechar (ou fechou enquanto o app estava em segundo plano).
  useEffect(() => {
    const candidateId =
      !isLoading && !session && error instanceof ApiError && error.status === 404
        ? lastSessionIdRef.current
        : null
    if (!candidateId || candidateId === dismissedSessionId || closedReceipt) return

    let cancelled = false
    apiClient
      .get(`/sessions/${candidateId}/receipt`)
      .then((receipt) => {
        if (!cancelled) setClosedReceipt(receipt)
      })
      .catch(() => {
        // sessao terminou em `error` (sem cobranca) ou recibo indisponivel por outro motivo -
        // so volta pro estado ocioso, sem forcar uma tela quebrada.
        if (!cancelled) {
          setDismissedSessionId(candidateId)
          sessionStorage.removeItem(LAST_ACTIVE_KEY)
        }
      })
    return () => {
      cancelled = true
    }
  }, [session, error, isLoading, dismissedSessionId, closedReceipt])

  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (session?.status !== 'active' && session?.status !== 'pending') return undefined
    const interval = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(interval)
  }, [session?.status])

  const isActive = session?.status === 'active'
  const hasTariff = session?.estimated_amount_due !== null && session?.estimated_amount_due !== undefined

  const valueRef = useRef(null)
  const elapsedRef = useRef(null)
  const prevValueRef = useRef(null)

  // Contagem ascendente do valor acumulado a cada atualizacao - em vez de trocar o numero
  // seco. `animateNumber` ja escreve direto no DOM (nao via estado React) e ja respeita
  // prefers-reduced-motion sozinho.
  useGSAP(() => {
    if (!isActive || !hasTariff || !valueRef.current) return
    const to = Number(session.estimated_amount_due)
    const from = prevValueRef.current ?? to
    animateNumber(valueRef.current, { from, to, ...MICRO, formatter: formatCurrency })
    prevValueRef.current = to
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.estimated_amount_due, isActive, hasTariff])

  // Transicao suave no texto do tempo decorrido a cada segundo - nao so troca seca do numero.
  useGSAP(() => {
    if (!elapsedRef.current || prefersReducedMotion()) return
    gsap.fromTo(
      elapsedRef.current,
      { autoAlpha: 0.5, y: -3 },
      { autoAlpha: 1, y: 0, overwrite: true, ...MICRO }
    )
  }, [tick])

  if (closedReceipt) {
    return (
      <SessionClosedConfirmation
        receipt={closedReceipt}
        onDismiss={() => {
          setDismissedSessionId(closedReceipt.session_id)
          setClosedReceipt(null)
          lastSessionIdRef.current = null
          sessionStorage.removeItem(LAST_ACTIVE_KEY)
          queryClient.invalidateQueries({ queryKey: ['sessions-mine'] })
        }}
      />
    )
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-5 p-5">
        <div className="flex items-center justify-between">
          <Skeleton className="h-7 w-40 rounded-full" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-12 w-48" />
        </div>
        <Skeleton className="h-14 w-full" />
      </div>
    )
  }

  if (error instanceof ApiError && error.status === 404) {
    return <NoActiveSession />
  }

  if (!session) {
    return <NoActiveSession />
  }

  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-status-carregando/10 px-3 py-1.5 text-xs font-medium text-status-carregando">
          <span className="cgm-pulse inline-block h-1.5 w-1.5 rounded-full bg-status-carregando" />
          {STATUS_LABEL[session.status] ?? session.status}
        </span>
        <span ref={elapsedRef} className="inline-block font-mono text-xs text-muted-2">
          {formatElapsed(session.started_at)}
        </span>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-2">
          Valor acumulado {isActive && '(estimado)'}
        </p>
        {isActive && hasTariff ? (
          <p ref={valueRef} className="mt-1 font-heading text-5xl font-bold leading-none text-ink" />
        ) : (
          <p className="mt-1 font-heading text-5xl font-bold leading-none text-ink">R$ —</p>
        )}
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

      <PaymentMethodPicker
        establishmentId={session.establishment_id}
        currentMethod={session.payment_method}
      />

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
