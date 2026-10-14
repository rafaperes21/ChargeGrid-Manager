import { useMemo, useState } from 'react'
import { formatPowerKw } from '../../lib/format'
import { ENERGY_COLORS } from './energyColors'

// Grafico do dia (00h-24h, horario local): carga dos carregadores empilhada por fonte
// (solar, bateria, rede), geracao solar total em linha tracejada e o limite contratado em
// linha de referencia. Mesmo estilo do PowerCurveChart (SVG puro, sem lib nova), com a mesma
// alternativa acessivel "ver como tabela".
const WIDTH = 640
const HEIGHT = 240
const PAD = { top: 14, right: 14, bottom: 26, left: 44 }
const PLOT_W = WIDTH - PAD.left - PAD.right
const PLOT_H = HEIGHT - PAD.top - PAD.bottom

const STACK = [
  { key: 'solar_to_load_kw', label: 'Solar → carga', color: ENERGY_COLORS.solar },
  { key: 'battery_to_load_kw', label: 'Bateria → carga', color: ENERGY_COLORS.battery },
  { key: 'grid_to_load_kw', label: 'Rede → carga', color: ENERGY_COLORS.grid },
]

const hourFormatter = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Sao_Paulo',
})

function localMinuteOfDay(iso) {
  const [h, m] = hourFormatter.format(new Date(iso)).split(':').map(Number)
  return h * 60 + m
}

export function EnergyDayChart({ series, gridLimitKw }) {
  const [showTable, setShowTable] = useState(false)

  const chart = useMemo(() => {
    if (series.length < 2) return null
    const limit = Number(gridLimitKw)
    const maxY =
      Math.max(
        limit,
        ...series.map((p) => Math.max(Number(p.solar_kw), Number(p.load_kw)))
      ) * 1.08
    const x = (iso) => PAD.left + (localMinuteOfDay(iso) / 1440) * PLOT_W
    const y = (v) => PAD.top + PLOT_H - (v / maxY) * PLOT_H

    const layers = []
    const base = series.map(() => 0)
    for (const layer of STACK) {
      const top = series.map((p, i) => base[i] + Number(p[layer.key]))
      const upper = series.map((p, i) => `${x(p.timestamp)},${y(top[i])}`)
      const lower = series.map((p, i) => `${x(p.timestamp)},${y(base[i])}`).reverse()
      layers.push({ ...layer, d: `M ${upper.join(' L ')} L ${lower.join(' L ')} Z` })
      top.forEach((v, i) => {
        base[i] = v
      })
    }
    const solarLine = series.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.timestamp)} ${y(Number(p.solar_kw))}`).join(' ')
    return { layers, solarLine, limitY: y(limit), y, maxY, limit }
  }, [series, gridLimitKw])

  if (!chart) {
    return (
      <div className="flex h-[240px] flex-col items-center justify-center gap-1.5 rounded-2xl border border-dashed border-hairline text-center">
        <p className="text-sm font-semibold text-ink-soft">Ainda sem leituras hoje</p>
        <p className="max-w-[320px] text-xs text-muted-2">
          O gráfico aparece quando o worker de polling gravar as primeiras leituras de fluxo do dia.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img" aria-label="Energia por fonte ao longo do dia">
        {[0, chart.maxY / 2].map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={chart.y(v)} y2={chart.y(v)} stroke="var(--color-hairline)" strokeDasharray="3 4" />
            <text x={PAD.left - 8} y={chart.y(v)} textAnchor="end" dominantBaseline="middle" className="fill-muted" fontSize="10">
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        {[0, 6, 12, 18, 24].map((h) => (
          <text key={h} x={PAD.left + (h / 24) * PLOT_W} y={HEIGHT - 8} textAnchor="middle" className="fill-muted" fontSize="10">
            {String(h).padStart(2, '0')}h
          </text>
        ))}
        {chart.layers.map((layer) => (
          <path key={layer.key} d={layer.d} fill={layer.color} fillOpacity="0.75" />
        ))}
        <path d={chart.solarLine} fill="none" stroke={ENERGY_COLORS.solar} strokeWidth="2" strokeDasharray="5 4" />
        <line x1={PAD.left} x2={WIDTH - PAD.right} y1={chart.limitY} y2={chart.limitY} stroke="var(--color-status-problema)" strokeWidth="1.5" strokeDasharray="8 5" />
        <text x={WIDTH - PAD.right} y={chart.limitY - 6} textAnchor="end" className="fill-muted-2" fontSize="10">
          limite contratado {chart.limit.toFixed(0)} kW
        </text>
      </svg>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-3 text-[11px] text-ink-soft">
          {STACK.map((layer) => (
            <span key={layer.key} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: layer.color }} />
              {layer.label}
            </span>
          ))}
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0 w-4 border-t-2 border-dashed" style={{ borderColor: ENERGY_COLORS.solar }} />
            geração solar total
          </span>
        </div>
        <button type="button" onClick={() => setShowTable((v) => !v)} className="text-[11px] font-semibold text-muted-2 underline">
          {showTable ? 'Ver gráfico' : 'Ver como tabela'}
        </button>
      </div>

      {showTable && (
        <div className="max-h-[200px] overflow-y-auto rounded-xl border border-hairline">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-cream text-muted">
              <tr>
                <th className="px-3 py-2 font-semibold">Horário</th>
                <th className="px-3 py-2 font-semibold">Carga</th>
                <th className="px-3 py-2 font-semibold">Solar</th>
                <th className="px-3 py-2 font-semibold">Bateria</th>
                <th className="px-3 py-2 font-semibold">Rede</th>
                <th className="px-3 py-2 font-semibold">SoC</th>
              </tr>
            </thead>
            <tbody>
              {[...series].reverse().map((p) => (
                <tr key={p.timestamp} className="border-t border-hairline text-ink-soft">
                  <td className="px-3 py-1.5">{hourFormatter.format(new Date(p.timestamp))}</td>
                  <td className="px-3 py-1.5">{formatPowerKw(p.load_kw)}</td>
                  <td className="px-3 py-1.5">{formatPowerKw(p.solar_kw)}</td>
                  <td className="px-3 py-1.5">{formatPowerKw(p.battery_kw)}</td>
                  <td className="px-3 py-1.5">{formatPowerKw(p.grid_to_load_kw)}</td>
                  <td className="px-3 py-1.5">{p.battery_soc_pct === null ? '—' : `${Number(p.battery_soc_pct).toFixed(0)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
