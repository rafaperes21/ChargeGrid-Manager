import L from 'leaflet'

// Pino do mapa (Tarefa I.1/2.2) reaproveita o mesmo desenho de src/assets/charger-pin.svg,
// mas embutido aqui como string pra poder trocar a cor via `fill` sem precisar de N arquivos
// estáticos - a cor segue os mesmos tokens de status usados em StatusBadge.
function pinSvg(fill) {
  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="30" height="30">
      <path
        d="M12 22s7-6.5 7-12.5A7 7 0 0 0 5 9.5C5 15.5 12 22 12 22Z"
        fill="${fill}" stroke="#ffffff" stroke-width="1.2"
      />
      <path d="M13 5.5 8.5 11h3l-1 5.5 4.5-6.5h-3l1-4.5Z" fill="#ffffff" />
    </svg>
  `
}

const iconCache = new Map()

export function createPinIcon(color) {
  if (iconCache.has(color)) return iconCache.get(color)
  const icon = L.divIcon({
    className: 'cgm-map-pin',
    html: pinSvg(color),
    iconSize: [30, 30],
    iconAnchor: [15, 28],
    popupAnchor: [0, -26],
  })
  iconCache.set(color, icon)
  return icon
}

// Tokens de status (index.css) - mesma paleta do StatusBadge, repetida aqui em hex porque o
// divIcon do Leaflet renderiza fora da árvore do React (sem acesso às classes Tailwind/CSS vars).
export const STATUS_PIN_COLOR = {
  livre: '#16a34a',
  carregando: '#2563eb',
  problema: '#dc2626',
  reservado: '#d97706',
  offline: '#6b7280',
}

export const BRAND_PIN_COLOR = '#7C3AED'
