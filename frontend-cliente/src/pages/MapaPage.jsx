import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../lib/apiClient'
import { formatDistanceKm, haversineDistanceKm } from '../lib/geo'

function useGeolocation() {
  const [state, setState] = useState({ status: 'loading', coords: null })

  useEffect(() => {
    if (!('geolocation' in navigator)) {
      setState({ status: 'unsupported', coords: null })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setState({
          status: 'granted',
          coords: { lat: position.coords.latitude, lon: position.coords.longitude },
        })
      },
      (error) => {
        setState({ status: error.code === error.PERMISSION_DENIED ? 'denied' : 'error', coords: null })
      },
      { enableHighAccuracy: false, timeout: 8000 }
    )
  }, [])

  return state
}

function EstablishmentCard({ establishment, distanceKm }) {
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
    <Link
      to={`/mapa/${establishment.id}`}
      className="flex items-center justify-between rounded-2xl border border-hairline p-3.5"
    >
      <div>
        <p className="text-sm font-semibold text-ink">{establishment.name}</p>
        <p className="mt-1 text-xs text-muted-2">
          {total} carregador{total !== 1 ? 'es' : ''} cadastrado{total !== 1 ? 's' : ''}
          {distanceKm != null && ` · ${formatDistanceKm(distanceKm)}`}
        </p>
      </div>
      <span className={`inline-flex items-center gap-1.5 rounded-full px-[11px] py-[5px] text-[11px] font-semibold ${badgeClass}`}>
        {badgeText}
      </span>
    </Link>
  )
}

function locationBannerText(status) {
  if (status === 'loading') return 'Localizando você…'
  if (status === 'granted') return 'Ordenado pelos mais próximos'
  if (status === 'denied') return 'Permissão de localização negada — ordem padrão'
  return 'Localização indisponível neste dispositivo — ordem padrão'
}

export function MapaPage() {
  const { data: establishments, isLoading } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
  })
  const location = useGeolocation()

  let sorted = establishments ?? []
  if (location.status === 'granted' && establishments) {
    sorted = [...establishments]
      .map((establishment) => ({
        establishment,
        distanceKm:
          establishment.latitude != null && establishment.longitude != null
            ? haversineDistanceKm(
                location.coords.lat,
                location.coords.lon,
                Number(establishment.latitude),
                Number(establishment.longitude)
              )
            : null,
      }))
      .sort((a, b) => {
        if (a.distanceKm == null) return 1
        if (b.distanceKm == null) return -1
        return a.distanceKm - b.distanceKm
      })
  } else {
    sorted = sorted.map((establishment) => ({ establishment, distanceKm: null }))
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="bg-ink-fixed px-5 pb-4 pt-[18px] text-white">
        <span className="text-[15px] font-semibold">Mapa</span>
        <div className="mt-3 flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-2.5">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="10" r="3" />
            <path d="M12 21s-7-6.05-7-11a7 7 0 0 1 14 0c0 4.95-7 11-7 11Z" />
          </svg>
          <span className="text-[13px] text-white/70">{locationBannerText(location.status)}</span>
        </div>
      </div>

      <div className="flex flex-col gap-3 p-5">
        {isLoading && <p className="text-sm text-muted">Carregando…</p>}
        {sorted.map(({ establishment, distanceKm }) => (
          <EstablishmentCard key={establishment.id} establishment={establishment} distanceKm={distanceKm} />
        ))}
        {establishments?.length === 0 && (
          <p className="text-sm text-muted">Nenhum estacionamento cadastrado ainda.</p>
        )}
      </div>
    </div>
  )
}
