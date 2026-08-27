import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { formatCurrency, formatPowerKw, formatUpdatedAgo } from '../lib/format'
import { animateNumber, gsap, MICRO, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'

const POWER_ALERT_THRESHOLD = 0.9

function secondsSince(isoString) {
  if (!isoString) return null
  return (Date.now() - new Date(isoString).getTime()) / 1000
}

export function DashboardPage() {
  const { establishment } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', establishment?.id],
    queryFn: () => apiClient.get(`/establishments/${establishment.id}/dashboard`),
    enabled: Boolean(establishment),
    refetchInterval: 20_000,
  })

  if (!establishment) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">
        Nenhum estabelecimento encontrado para este usuário.
      </div>
    )
  }

  if (isLoading || !data) {
    return <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted">Carregando…</div>
  }

  const powerPct = data.power_pct !== null ? Number(data.power_pct) : null
  const overThreshold = powerPct !== null && powerPct >= POWER_ALERT_THRESHOLD

  return <DashboardContent data={data} powerPct={powerPct} overThreshold={overThreshold} />
}

function DashboardContent({ data, powerPct, overThreshold }) {
  const fillRef = useRef(null)
  const prevPctRef = useRef(0)
  const alertRef = useRef(null)
  const anomaliesRef = useRef(null)
  const revenueTodayRef = useRef(null)
  const revenueWeekRef = useRef(null)
  const revenueMonthRef = useRef(null)
  const prevRevenueRef = useRef({ today: null, week: null, month: null })

  // Barra de potencia: anima a largura preenchida (via scaleX + transformOrigin - transform
  // e mais performatico que animar `width` direto) toda vez que power_pct muda.
  useGSAP(() => {
    if (!fillRef.current) return
    const to = Math.min(1, powerPct ?? 0)
    gsap.set(fillRef.current, { scaleX: prevPctRef.current, transformOrigin: 'left center' })
    gsap.to(fillRef.current, { scaleX: to, ...MICRO })
    prevPctRef.current = to
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [powerPct])

  // Alerta de 90%: pulso suave e continuo enquanto ativo, para sozinho quando o alerta some
  // (useGSAP limpa a animacao no unmount).
  useGSAP(() => {
    if (!alertRef.current || prefersReducedMotion()) return
    const tween = gsap.to(alertRef.current, {
      scale: 1.015,
      duration: 1,
      ease: 'sine.inOut',
      repeat: -1,
      yoyo: true,
    })
    return () => tween.kill()
  }, [])

  // Cards de anomalia: entrada com leve slide+fade ao aparecer.
  useGSAP(() => {
    if (!anomaliesRef.current) return
    const cards = anomaliesRef.current.querySelectorAll('[data-anomaly-card]')
    if (cards.length === 0) return
    gsap.fromTo(cards, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, stagger: 0.06, ...TRANSITION })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.anomalies.length])

  // Receita hoje/semana/mes: contagem ascendente a cada atualizacao, mesma funcao de motion.js
  // usada na sessao do cliente.
  useGSAP(() => {
    const targets = [
      [revenueTodayRef, data.revenue_today, 'today'],
      [revenueWeekRef, data.revenue_week, 'week'],
      [revenueMonthRef, data.revenue_month, 'month'],
    ]
    for (const [ref, value, key] of targets) {
      const to = Number(value)
      const from = prevRevenueRef.current[key] ?? to
      animateNumber(ref.current, { from, to, ...MICRO, formatter: formatCurrency })
      prevRevenueRef.current[key] = to
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.revenue_today, data.revenue_week, data.revenue_month])

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[23px] font-bold text-ink">Dashboard</h1>
          <p className="mt-1 text-[13px] text-muted-2">{data.establishment_name}</p>
        </div>
      </div>

      <div className="flex flex-col gap-5 p-8">
        {overThreshold && (
          <div
            ref={alertRef}
            className="flex items-center gap-2.5 rounded-2xl border border-status-reservado bg-amber-100 px-[18px] py-[13px]"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#92400E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
              <path d="M12 9v4" />
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L14.71 3.86a2 2 0 0 0-3.42 0Z" />
              <path d="M12 17h.01" />
            </svg>
            <span className="text-[13px] text-amber-900">
              <strong>Potência total em {Math.round(powerPct * 100)}% do limite contratado</strong> —{' '}
              {formatPowerKw(data.total_power_kw)} / {formatPowerKw(data.power_limit_kw)}. Alerta permanece
              visível acima de 90%.
            </span>
          </div>
        )}

        <div className="grid grid-cols-[1.7fr_1fr_1fr] gap-4">
          <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Potência atual / limite
                </p>
                <p className="mt-1.5 font-heading text-[28px] font-bold text-ink">
                  {Number(data.total_power_kw).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                  <span className="text-base font-medium text-muted"> / {formatPowerKw(data.power_limit_kw)}</span>
                </p>
              </div>
              <span className="flex items-center gap-1.5 font-mono text-[11px] text-muted">
                <span className="cgm-pulse inline-block h-1.5 w-1.5 rounded-full bg-brand" />
                dado real do simulador
              </span>
            </div>
            <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-hairline">
              <div
                ref={fillRef}
                className="h-2.5 w-full origin-left rounded-full"
                style={{
                  transform: 'scaleX(0)',
                  background: 'linear-gradient(90deg,#7C3AED,#E60012,#FF7A1A)',
                }}
              />
            </div>
            <p className="mt-1.5 text-[10px] text-muted">limiar 90% marcado</p>
          </div>

          <div className="flex flex-col justify-center rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Receita hoje</p>
            <p ref={revenueTodayRef} className="mt-1.5 font-heading text-[28px] font-bold text-ink" />
            <p className="mt-1.5 text-[11px] text-muted-2">
              semana <span ref={revenueWeekRef} /> · mês <span ref={revenueMonthRef} />
            </p>
          </div>

          <div className="flex flex-col justify-center rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Sessões ativas</p>
            <p className="mt-1.5 font-heading text-[28px] font-bold text-ink">
              {data.active_sessions_count}
            </p>
          </div>
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-heading text-base font-semibold text-ink">Mapa de vagas</h2>
            <p className="text-[11px] text-muted">clique num carregador pra ver o detalhe</p>
          </div>
          <div className="grid grid-cols-4 gap-3 lg:grid-cols-8">
            {data.chargers.map((charger) => (
              <Link
                key={charger.id}
                to={`/carregadores/${charger.id}`}
                className="rounded-2xl border border-hairline bg-surface p-3.5 transition-shadow hover:shadow-[0_4px_16px_rgba(14,10,26,0.08)]"
              >
                <p className="mb-2 font-mono text-[13px] font-semibold text-ink">{charger.spot_label}</p>
                <StatusBadge status={charger.status} />
                {charger.latest_power_kw !== null && Number(charger.latest_power_kw) > 0 && (
                  <>
                    <p className="mt-1.5 font-mono text-[11px] text-ink-soft">
                      {formatPowerKw(charger.latest_power_kw)}
                    </p>
                    <p className="mt-0.5 text-[10px] text-muted">
                      {formatUpdatedAgo(secondsSince(charger.latest_reading_at))}
                    </p>
                  </>
                )}
              </Link>
            ))}
            {data.chargers.length === 0 && (
              <p className="col-span-full text-sm text-muted">Nenhum carregador cadastrado.</p>
            )}
          </div>
        </div>

        <div>
          <h2 className="mb-3 font-heading text-base font-semibold text-ink">Alertas da IA</h2>
          {data.ia_unavailable && (
            <p className="mb-2 text-xs text-muted">
              Serviço de IA fora do ar no momento — dashboard segue funcionando normalmente.
            </p>
          )}
          <div
            ref={anomaliesRef}
            className="overflow-hidden rounded-[22px] border border-hairline bg-surface shadow-[0_4px_20px_rgba(14,10,26,0.05)]"
          >
            {data.anomalies.length === 0 ? (
              <p className="px-[18px] py-4 text-sm text-muted">Nenhuma anomalia detectada.</p>
            ) : (
              data.anomalies.map((anomaly, index) => (
                <div
                  key={index}
                  data-anomaly-card
                  className="flex items-center justify-between border-b border-[#F4F2FB] px-[18px] py-3.5 last:border-b-0"
                >
                  <div>
                    <p className="text-[13px] font-semibold text-ink">{anomaly.charger_serial}</p>
                    <p className="text-xs text-muted-2">{anomaly.message}</p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      anomaly.severity === 'high' ? 'bg-status-problema/10 text-status-problema' : 'bg-status-reservado/10 text-status-reservado'
                    }`}
                  >
                    {anomaly.severity === 'high' ? 'Alta' : 'Média'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
