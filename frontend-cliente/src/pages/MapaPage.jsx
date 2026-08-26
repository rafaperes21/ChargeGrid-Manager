import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'

function EstablishmentCard({ establishment }) {
  const { data: chargers } = useQuery({
    queryKey: ['chargers', establishment.id],
    queryFn: () => apiClient.get(`/chargers?establishment_id=${establishment.id}`),
  })

  const total = chargers?.length ?? 0
  const free = chargers?.filter((c) => c.status === 'livre').length ?? 0
  const anyOnline = chargers?.some((c) => c.status !== 'offline') ?? true

  let badgeText = '…'
  let badgeClass = 'bg-[#F4F2FB] text-muted-2'
  if (chargers) {
    if (!anyOnline) {
      badgeText = '○ Offline'
      badgeClass = 'bg-status-offline/10 text-status-offline'
    } else if (free > 0) {
      badgeText = `● ${free} livre${free > 1 ? 's' : ''}`
      badgeClass = 'bg-status-livre/10 text-status-livre'
    } else {
      badgeText = '○ sem vagas'
      badgeClass = 'bg-status-offline/10 text-status-offline'
    }
  }

  return (
    <div className="flex items-center justify-between rounded-2xl border border-hairline p-3.5">
      <div>
        <p className="text-sm font-semibold text-ink">{establishment.name}</p>
        <p className="mt-1 text-xs text-muted-2">{total} carregador{total !== 1 ? 'es' : ''} cadastrado{total !== 1 ? 's' : ''}</p>
      </div>
      <span className={`inline-flex items-center gap-1.5 rounded-full px-[11px] py-[5px] text-[11px] font-semibold ${badgeClass}`}>
        {badgeText}
      </span>
    </div>
  )
}

export function MapaPage() {
  const { data: establishments, isLoading } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
  })

  return (
    <div className="flex flex-1 flex-col">
      <div className="bg-ink px-5 pb-4 pt-[18px] text-white">
        <span className="text-[15px] font-semibold">Mapa</span>
        <div className="mt-3 flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-2.5">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <span className="text-[13px] text-white/70">Distância e busca chegam numa próxima versão</span>
        </div>
      </div>

      <div className="flex flex-col gap-3 p-5">
        {isLoading && <p className="text-sm text-muted">Carregando…</p>}
        {establishments?.map((establishment) => (
          <EstablishmentCard key={establishment.id} establishment={establishment} />
        ))}
        {establishments?.length === 0 && (
          <p className="text-sm text-muted">Nenhum estacionamento cadastrado ainda.</p>
        )}
      </div>
    </div>
  )
}
