import { useRef } from 'react'
import { formatPowerKw } from '../../lib/format'
import { gsap, prefersReducedMotion, useGSAP } from '../../lib/motion'
import { ENERGY_COLORS } from './energyColors'

// Diagrama do fluxo de energia (solar -> bateria -> carregadores <- rede) a partir da ultima
// leitura real de `site_energy_readings`. Cada ligacao tem espessura e velocidade do
// tracejado proporcionais ao kW; ligacao sem fluxo fica apagada (nao some, pra o operador
// ver que existe e esta parada). Valores sempre em texto ao lado da linha.
const W = 640
const H = 320
const HUB = { x: 320, y: 160 }
const NODES = {
  solar: { x: 110, y: 64, label: 'Solar', sub: 'inversor' },
  grid: { x: 530, y: 64, label: 'Rede', sub: 'distribuidora' },
  battery: { x: 110, y: 256, label: 'Bateria', sub: '' },
  load: { x: 530, y: 256, label: 'Carregadores', sub: 'HCA G2' },
}

function toNumber(value) {
  return value === null || value === undefined ? 0 : Number(value)
}

function buildEdges(point) {
  const batteryKw = toNumber(point.battery_kw)
  const gridIn = toNumber(point.grid_to_load_kw)
  const surplus = toNumber(point.solar_surplus_kw)
  return [
    { id: 'solar', node: 'solar', kw: toNumber(point.solar_kw), towardHub: true, color: ENERGY_COLORS.solar },
    {
      id: 'battery',
      node: 'battery',
      kw: Math.abs(batteryKw),
      towardHub: batteryKw > 0, // descarregando: bateria -> quadro
      color: ENERGY_COLORS.battery,
      caption: batteryKw > 0 ? 'descarregando' : batteryKw < 0 ? 'carregando' : 'parada',
    },
    {
      id: 'grid',
      node: 'grid',
      kw: gridIn > 0 ? gridIn : surplus,
      towardHub: gridIn > 0 || surplus === 0,
      color: ENERGY_COLORS.grid,
      caption: gridIn > 0 ? 'importando' : surplus > 0 ? 'excedente solar' : 'sem troca',
    },
    { id: 'load', node: 'load', kw: toNumber(point.load_kw), towardHub: false, color: ENERGY_COLORS.load },
  ]
}

export function EnergyFlowDiagram({ point, socPct }) {
  const svgRef = useRef(null)
  const edges = buildEdges(point)
  const maxKw = Math.max(1, ...edges.map((e) => e.kw))
  const animationKey = edges.map((e) => `${e.id}:${e.kw}:${e.towardHub}`).join('|')

  // Tracejado "andando" na direcao do fluxo, mais rapido quanto maior o kW. Recria a cada
  // leitura nova (key muda) - useGSAP mata as tweens antigas sozinho.
  useGSAP(
    () => {
      if (prefersReducedMotion()) return
      edges.forEach((edge) => {
        const el = svgRef.current?.querySelector(`[data-flow="${edge.id}"]`)
        if (!el || edge.kw <= 0) return
        const speed = 0.6 + (1 - edge.kw / maxKw) * 1.6 // s por ciclo: 0,6 (max) a 2,2
        gsap.fromTo(
          el,
          { strokeDashoffset: 0 },
          { strokeDashoffset: edge.towardHub ? -24 : 24, duration: speed, ease: 'none', repeat: -1 }
        )
      })
    },
    { scope: svgRef, dependencies: [animationKey] }
  )

  return (
    <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Fluxo de energia do estabelecimento">
      {edges.map((edge) => {
        const node = NODES[edge.node]
        const active = edge.kw > 0
        const width = active ? 2 + (edge.kw / maxKw) * 6 : 2
        const midX = (node.x + HUB.x) / 2
        const midY = (node.y + HUB.y) / 2
        return (
          <g key={edge.id}>
            <line
              x1={node.x}
              y1={node.y}
              x2={HUB.x}
              y2={HUB.y}
              stroke="var(--color-hairline)"
              strokeWidth={width + 4}
              strokeLinecap="round"
            />
            <line
              data-flow={edge.id}
              x1={node.x}
              y1={node.y}
              x2={HUB.x}
              y2={HUB.y}
              stroke={edge.color}
              strokeOpacity={active ? 1 : 0.25}
              strokeWidth={width}
              strokeLinecap="round"
              strokeDasharray={active ? '10 14' : '2 8'}
            />
            <g transform={`translate(${midX}, ${midY - 12})`}>
              <rect x="-50" y="-11" width="100" height="22" rx="11" fill="var(--color-surface)" stroke="var(--color-hairline)" />
              <text textAnchor="middle" dominantBaseline="central" className="fill-ink" fontSize="12" fontWeight="600">
                {formatPowerKw(edge.kw)}
              </text>
            </g>
            {edge.caption && (
              <text x={midX} y={midY + 14} textAnchor="middle" className="fill-muted" fontSize="10">
                {edge.caption}
              </text>
            )}
          </g>
        )
      })}

      <circle cx={HUB.x} cy={HUB.y} r="26" fill="var(--color-surface)" stroke="var(--color-hairline)" strokeWidth="2" />
      <text x={HUB.x} y={HUB.y} textAnchor="middle" dominantBaseline="central" className="fill-muted-2" fontSize="10" fontWeight="600">
        quadro
      </text>

      {Object.entries(NODES).map(([key, node]) => {
        const color = ENERGY_COLORS[key]
        const sub = key === 'battery' && socPct !== null && socPct !== undefined ? `SoC ${Number(socPct).toFixed(0)}%` : node.sub
        return (
          <g key={key} transform={`translate(${node.x}, ${node.y})`}>
            <rect x="-62" y="-30" width="124" height="60" rx="16" fill="var(--color-surface)" stroke={color} strokeWidth="2" />
            <text y="-6" textAnchor="middle" className="fill-ink" fontSize="14" fontWeight="700">
              {node.label}
            </text>
            <text y="13" textAnchor="middle" className="fill-muted-2" fontSize="11">
              {sub}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
