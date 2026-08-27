import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PowerCurveChart } from '../components/charts/PowerCurveChart'
import { Skeleton } from '../components/ui/Skeleton'
import { StatusBadge } from '../components/ui/StatusBadge'
import { apiClient } from '../lib/apiClient'
import {
  formatCurrency,
  formatDateTime,
  formatEnergyKwh,
  formatPowerKw,
  formatUpdatedAgo,
} from '../lib/format'
import { animateNumber, gsap, MICRO, prefersReducedMotion, TRANSITION, useGSAP } from '../lib/motion'

const DEFAULT_WINDOW_HOURS = 24

// Presets de janela pro grafico de curva de potencia - a demo tem historico de semanas
// (backfill de ChargerReading a partir das sessoes, ver seed_demo_history.py), 24h sozinho
// mostraria so uma fatia fina na maior parte do tempo.
const WINDOW_PRESETS = [
  { label: '24h', hours: 24 },
  { label: '7 dias', hours: 24 * 7 },
  { label: '30 dias', hours: 24 * 30 },
]

function secondsSince(isoString) {
  if (!isoString) return null
  return (Date.now() - new Date(isoString).getTime()) / 1000
}

function UptimeTile({ uptimePct, windowHours }) {
  const valueRef = useRef(null)
  const prevRef = useRef(null)

  useGSAP(() => {
    if (!valueRef.current || uptimePct === null) return
    const to = Math.round(Number(uptimePct) * 1000) / 10
    const from = prevRef.current ?? to
    animateNumber(valueRef.current, {
      from,
      to,
      ...MICRO,
      formatter: (v) => `${v.toFixed(1)}%`,
    })
    prevRef.current = to
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uptimePct])

  return (
    <div className="flex flex-col justify-center rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
        Uptime ({WINDOW_PRESETS.find((preset) => preset.hours === windowHours)?.label ?? `${windowHours}h`})
      </p>
      {uptimePct === null ? (
        <>
          <p className="mt-1.5 font-heading text-2xl font-bold text-muted-3">—</p>
          <p className="mt-1 text-[11px] text-muted-2">coletando dados</p>
        </>
      ) : (
        <p ref={valueRef} className="mt-1.5 font-heading text-[28px] font-bold text-ink" />
      )}
    </div>
  )
}

function ChargerDetailContent({ data, windowHours, onChangeWindowHours }) {
  const anomaliesRef = useRef(null)
  const sessionsRef = useRef(null)

  useGSAP(() => {
    if (!anomaliesRef.current) return
    const cards = anomaliesRef.current.querySelectorAll('[data-anomaly-card]')
    if (cards.length === 0) return
    gsap.fromTo(cards, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, stagger: 0.06, ...TRANSITION })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.anomalies.length])

  useGSAP(() => {
    if (!sessionsRef.current || prefersReducedMotion()) return
    gsap.fromTo(sessionsRef.current, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, ...TRANSITION })
  }, [data.id])

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <Link to="/" className="text-xs font-semibold text-muted-2">
            ← Dashboard
          </Link>
          <h1 className="mt-1 font-heading text-[23px] font-bold text-ink">{data.spot_label}</h1>
          <p className="mt-1 text-[13px] text-muted-2">
            {data.model} · {data.sems_serial}
          </p>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Potência atual / nominal
            </p>
            <p className="mt-1.5 font-heading text-[28px] font-bold text-ink">
              {data.latest_power_kw !== null ? formatPowerKw(data.latest_power_kw) : '—'}
              <span className="text-base font-medium text-muted"> / {formatPowerKw(data.nominal_power_kw)}</span>
            </p>
            {data.latest_reading_at && (
              <p className="mt-1.5 text-[11px] text-muted">
                {formatUpdatedAgo(secondsSince(data.latest_reading_at))}
              </p>
            )}
          </div>

          <UptimeTile uptimePct={data.uptime_pct} windowHours={data.readings_window_hours} />

          <div className="flex flex-col justify-center rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Sessões recentes</p>
            <p className="mt-1.5 font-heading text-[28px] font-bold text-ink">{data.recent_sessions.length}</p>
          </div>
        </div>

        <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-heading text-base font-semibold text-ink">Curva de potência</h2>
            <div className="flex gap-1 rounded-full bg-cream p-1">
              {WINDOW_PRESETS.map((preset) => (
                <button
                  key={preset.hours}
                  type="button"
                  onClick={() => onChangeWindowHours(preset.hours)}
                  className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                    windowHours === preset.hours ? 'bg-brand text-white' : 'text-muted-2'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
          <PowerCurveChart
            points={data.power_readings}
            nominalKw={data.nominal_power_kw}
            windowHours={data.readings_window_hours}
          />
        </div>

        <div>
          <h2 className="mb-3 font-heading text-base font-semibold text-ink">Anomalias deste carregador</h2>
          {data.ia_unavailable && (
            <p className="mb-2 text-xs text-muted">
              Serviço de IA fora do ar no momento — tela segue funcionando normalmente.
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
                  <p className="text-xs text-muted-2">{anomaly.message}</p>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      anomaly.severity === 'high'
                        ? 'bg-status-problema/10 text-status-problema'
                        : 'bg-status-reservado/10 text-status-reservado'
                    }`}
                  >
                    {anomaly.severity === 'high' ? 'Alta' : 'Média'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div ref={sessionsRef}>
          <h2 className="mb-3 font-heading text-base font-semibold text-ink">Últimas sessões</h2>
          <div className="overflow-hidden rounded-[22px] border border-hairline bg-surface shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
            {data.recent_sessions.length === 0 ? (
              <p className="px-[18px] py-4 text-sm text-muted">Nenhuma sessão registrada neste carregador ainda.</p>
            ) : (
              data.recent_sessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between border-b border-[#F4F2FB] px-[18px] py-3.5 last:border-b-0"
                >
                  <div>
                    <p className="text-[13px] font-semibold text-ink">{formatDateTime(session.started_at)}</p>
                    <p className="text-xs text-muted-2">
                      {session.energy_kwh !== null ? formatEnergyKwh(session.energy_kwh) : '—'}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-ink">
                    {session.amount_due !== null ? formatCurrency(session.amount_due) : '—'}
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

export function ChargerDetalhePage() {
  const { chargerId } = useParams()
  const [windowHours, setWindowHours] = useState(DEFAULT_WINDOW_HOURS)

  const { data, isLoading } = useQuery({
    queryKey: ['charger-detail', chargerId, windowHours],
    queryFn: () => apiClient.get(`/chargers/${chargerId}/detail?hours=${windowHours}`),
    refetchInterval: 20_000,
  })

  if (isLoading || !data) {
    return (
      <div className="flex flex-1 flex-col gap-5 p-8">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <ChargerDetailContent data={data} windowHours={windowHours} onChangeWindowHours={setWindowHours} />
  )
}
