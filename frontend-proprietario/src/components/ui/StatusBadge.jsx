// Os cinco status de carregador da skill ui-dois-portais. Cor nunca é o único sinal —
// por isso todo status carrega ícone + rótulo em texto, mesmo aqui no template.
const STATUS_CONFIG = {
  livre: { label: 'Livre', icon: '●', className: 'bg-status-livre/10 text-status-livre' },
  carregando: { label: 'Carregando', icon: '▶', className: 'bg-status-carregando/10 text-status-carregando' },
  problema: { label: 'Problema', icon: '✕', className: 'bg-status-problema/10 text-status-problema' },
  reservado: { label: 'Reservado', icon: '◐', className: 'bg-status-reservado/10 text-status-reservado' },
  offline: { label: 'Offline', icon: '○', className: 'bg-status-offline/10 text-status-offline' },
}

export function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status]
  if (!config) throw new Error(`Status de carregador desconhecido: ${status}`)

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${config.className}`}
    >
      <span aria-hidden="true">{config.icon}</span>
      {config.label}
    </span>
  )
}
