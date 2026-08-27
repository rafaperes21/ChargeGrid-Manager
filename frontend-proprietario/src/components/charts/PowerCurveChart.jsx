import { useMemo, useRef, useState } from 'react'
import { formatDateTime, formatPowerKw } from '../../lib/format'
import { gsap, prefersReducedMotion, useGSAP } from '../../lib/motion'

// Grafico de linha animado - potencia real (nunca interpolada) ao longo do tempo pra um
// carregador. Serie unica: uma cor so (marca), sem necessidade de legenda (skill dataviz,
// "single series needs no legend box"). Sem lib de grafico nova - mesma tecnica de
// stroke-dasharray/pathLength=1 ja usada no check de confirmacao de sessao do cliente.
const LINE_COLOR = '#7C3AED'
const WIDTH = 600
const HEIGHT = 220
const PADDING = { top: 16, right: 16, bottom: 12, left: 44 }

function buildScales(points, nominalKw) {
  const plotWidth = WIDTH - PADDING.left - PADDING.right
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom
  const times = points.map((p) => new Date(p.timestamp).getTime())
  const minT = Math.min(...times)
  const maxT = Math.max(...times)
  const maxPower = Math.max(Number(nominalKw), ...points.map((p) => Number(p.power_kw))) * 1.05

  const x = (t) =>
    PADDING.left + (maxT === minT ? plotWidth / 2 : ((t - minT) / (maxT - minT)) * plotWidth)
  const y = (v) => PADDING.top + plotHeight - (maxPower === 0 ? 0 : (v / maxPower) * plotHeight)
  return { x, y, plotHeight, maxPower }
}

export function PowerCurveChart({ points, nominalKw, windowHours }) {
  const [hoverIndex, setHoverIndex] = useState(null)
  const [showTable, setShowTable] = useState(false)
  const pathRef = useRef(null)
  const areaRef = useRef(null)
  const dotRef = useRef(null)

  const scales = useMemo(
    () => (points.length >= 2 ? buildScales(points, nominalKw) : null),
    [points, nominalKw]
  )

  const linePath = useMemo(() => {
    if (!scales) return ''
    return points
      .map((p, i) => {
        const command = i === 0 ? 'M' : 'L'
        return `${command} ${scales.x(new Date(p.timestamp).getTime())} ${scales.y(Number(p.power_kw))}`
      })
      .join(' ')
  }, [points, scales])

  const areaPath = useMemo(() => {
    if (!scales || points.length < 2) return ''
    const baseline = PADDING.top + scales.plotHeight
    const first = scales.x(new Date(points[0].timestamp).getTime())
    const last = scales.x(new Date(points[points.length - 1].timestamp).getTime())
    return `${linePath} L ${last} ${baseline} L ${first} ${baseline} Z`
  }, [linePath, scales, points])

  // Desenho animado da linha (stroke-dashoffset 1 -> 0, pathLength normalizado) + fade do
  // preenchimento em gradiente - roda de novo só quando o path muda de verdade (nao a cada
  // refetch identico).
  useGSAP(() => {
    if (!pathRef.current || !scales) return
    if (prefersReducedMotion()) {
      gsap.set([pathRef.current, areaRef.current], { strokeDashoffset: 0, autoAlpha: 1 })
      return
    }
    gsap.set(pathRef.current, { strokeDashoffset: 1 })
    gsap.set(areaRef.current, { autoAlpha: 0 })
    const tl = gsap.timeline()
    tl.to(pathRef.current, { strokeDashoffset: 0, duration: 1.1, ease: 'power2.out' })
    tl.to(areaRef.current, { autoAlpha: 1, duration: 0.5 }, '-=0.4')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linePath])

  // Ponto "ao vivo" no ultimo valor - pulso continuo, mesmo padrao do indicador
  // "dado real do simulador" do Dashboard.
  useGSAP(() => {
    if (!dotRef.current || prefersReducedMotion()) return
    const tween = gsap.to(dotRef.current, {
      scale: 1.7,
      opacity: 0.35,
      duration: 1,
      ease: 'sine.inOut',
      repeat: -1,
      yoyo: true,
      transformOrigin: 'center',
    })
    return () => tween.kill()
  }, [scales])

  if (!scales) {
    return (
      <div className="flex h-[220px] flex-col items-center justify-center gap-1.5 rounded-2xl border border-dashed border-hairline text-center">
        <p className="text-sm font-semibold text-ink-soft">Coletando dados de potência</p>
        <p className="max-w-[280px] text-xs text-muted-2">
          Leituras a cada 60s desde que este ambiente começou a rodar — ainda não há histórico
          suficiente pra desenhar a curva.
        </p>
      </div>
    )
  }

  const lastPoint = points[points.length - 1]
  const hovered = hoverIndex !== null ? points[hoverIndex] : null
  const nominal = Number(nominalKw)
  const gridValues = [...new Set([0, scales.maxPower / 2, nominal > 0 ? nominal : scales.maxPower])]

  function handleMove(event) {
    const rect = event.currentTarget.getBoundingClientRect()
    const relX = ((event.clientX - rect.left) / rect.width) * WIDTH
    let closest = 0
    let closestDist = Infinity
    points.forEach((p, i) => {
      const dist = Math.abs(scales.x(new Date(p.timestamp).getTime()) - relX)
      if (dist < closestDist) {
        closestDist = dist
        closest = i
      }
    })
    setHoverIndex(closest)
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full cursor-crosshair"
          onMouseMove={handleMove}
          onMouseLeave={() => setHoverIndex(null)}
        >
          <defs>
            <linearGradient id="power-curve-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={LINE_COLOR} stopOpacity="0.22" />
              <stop offset="100%" stopColor={LINE_COLOR} stopOpacity="0" />
            </linearGradient>
          </defs>

          {gridValues.map((value) => (
            <g key={value}>
              <line
                x1={PADDING.left}
                x2={WIDTH - PADDING.right}
                y1={scales.y(value)}
                y2={scales.y(value)}
                stroke="var(--color-hairline)"
                strokeWidth="1"
                strokeDasharray="3 4"
              />
              <text
                x={PADDING.left - 8}
                y={scales.y(value)}
                textAnchor="end"
                dominantBaseline="middle"
                className="fill-muted"
                fontSize="10"
              >
                {value.toFixed(1)}
              </text>
            </g>
          ))}

          <path ref={areaRef} d={areaPath} fill="url(#power-curve-fill)" />
          <path
            ref={pathRef}
            d={linePath}
            fill="none"
            stroke={LINE_COLOR}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength="1"
            style={{ strokeDasharray: 1 }}
          />

          <circle
            ref={dotRef}
            cx={scales.x(new Date(lastPoint.timestamp).getTime())}
            cy={scales.y(Number(lastPoint.power_kw))}
            r="4"
            fill={LINE_COLOR}
          />

          {hovered && (
            <g>
              <line
                x1={scales.x(new Date(hovered.timestamp).getTime())}
                x2={scales.x(new Date(hovered.timestamp).getTime())}
                y1={PADDING.top}
                y2={PADDING.top + scales.plotHeight}
                stroke="var(--color-muted-3)"
                strokeWidth="1"
              />
              <circle
                cx={scales.x(new Date(hovered.timestamp).getTime())}
                cy={scales.y(Number(hovered.power_kw))}
                r="4"
                fill="var(--color-surface)"
                stroke={LINE_COLOR}
                strokeWidth="2"
              />
            </g>
          )}
        </svg>

        {hovered && (
          <div
            className="pointer-events-none absolute top-1 rounded-lg border border-hairline bg-surface px-2.5 py-1.5 text-[11px] shadow-[0_4px_16px_rgba(14,10,26,0.12)]"
            style={{
              left: `${(scales.x(new Date(hovered.timestamp).getTime()) / WIDTH) * 100}%`,
              transform: 'translateX(-50%)',
            }}
          >
            <p className="font-semibold text-ink">{formatPowerKw(hovered.power_kw)}</p>
            <p className="text-muted-2">{formatDateTime(hovered.timestamp)}</p>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-[11px] text-muted">
          últimas {windowHours}h · {points.length} leitura{points.length !== 1 ? 's' : ''}
        </p>
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="text-[11px] font-semibold text-muted-2 underline"
        >
          {showTable ? 'Ver gráfico' : 'Ver como tabela'}
        </button>
      </div>

      {showTable && (
        <div className="max-h-[160px] overflow-y-auto rounded-xl border border-hairline">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-cream text-muted">
              <tr>
                <th className="px-3 py-2 font-semibold">Horário</th>
                <th className="px-3 py-2 font-semibold">Potência</th>
              </tr>
            </thead>
            <tbody>
              {[...points].reverse().map((p) => (
                <tr key={p.timestamp} className="border-t border-hairline">
                  <td className="px-3 py-1.5 text-ink-soft">{formatDateTime(p.timestamp)}</td>
                  <td className="px-3 py-1.5 text-ink-soft">{formatPowerKw(p.power_kw)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
