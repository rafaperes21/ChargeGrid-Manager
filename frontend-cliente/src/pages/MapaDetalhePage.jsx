import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { StatusBadge } from '../components/ui/StatusBadge'
import { ApiError, apiClient } from '../lib/apiClient'
import { formatDateTime, formatPowerKw, formatUpdatedAgo } from '../lib/format'
import { createPinIcon, STATUS_PIN_COLOR } from '../lib/mapIcons'
import { startSessionErrorMessage } from '../lib/sessionErrors'

// O backend so guarda uma coordenada por estabelecimento (Establishment.latitude/longitude) -
// nao existe coordenada individual por carregador (ver Charger model). Pra dar um pino por
// carregador sem inventar GPS que o sistema nao tem, espalhamos os pinos num pequeno circulo
// em torno do ponto real do estabelecimento (~50m de raio) - so um recurso visual de
// agrupamento, nunca apresentado como localizacao precisa. Documentado em
// tasks/milestones/M10-motion-mapa-3d.md.
function chargerPinOffset(index, total) {
  if (total <= 1) return [0, 0]
  const angle = (2 * Math.PI * index) / total
  const radiusDeg = 0.00045
  return [radiusDeg * Math.sin(angle), radiusDeg * Math.cos(angle)]
}

function ChargersMiniMap({ establishment, chargers }) {
  if (establishment?.latitude == null || establishment?.longitude == null) return null

  const center = [Number(establishment.latitude), Number(establishment.longitude)]

  return (
    <div className="h-[200px] w-full overflow-hidden rounded-2xl border border-hairline">
      <MapContainer center={center} zoom={17} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {chargers.map((charger, index) => {
          const [dLat, dLon] = chargerPinOffset(index, chargers.length)
          return (
            <Marker
              key={charger.id}
              position={[center[0] + dLat, center[1] + dLon]}
              icon={createPinIcon(STATUS_PIN_COLOR[charger.status] ?? STATUS_PIN_COLOR.offline)}
            >
              <Popup>
                <p className="font-semibold">{charger.spot_label}</p>
                <p>{charger.status}</p>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}

function secondsSince(iso) {
  if (!iso) return null
  return (Date.now() - new Date(iso).getTime()) / 1000
}

// Tela somente-leitura de status por carregador (Tarefa 2.2) - reaproveita o mesmo dado
// de `GET /establishments/{id}/chargers-status`, que por sua vez reusa a leitura do
// dashboard do proprietario (`services/dashboard.get_chargers_status`), sem receita nem
// anomalias por nao ser dado do dono.
function ReservationForm({ chargerId, onDone }) {
  const queryClient = useQueryClient()
  const [start, setStart] = useState('')
  const [durationMin, setDurationMin] = useState(60)
  const [errorMessage, setErrorMessage] = useState(null)

  const mutation = useMutation({
    mutationFn: () => {
      const scheduledStart = new Date(start)
      const scheduledEnd = new Date(scheduledStart.getTime() + durationMin * 60_000)
      return apiClient.post('/reservations', {
        charger_id: chargerId,
        scheduled_start: scheduledStart.toISOString(),
        scheduled_end: scheduledEnd.toISOString(),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reservations-mine'] })
      onDone()
    },
    onError: (error) => {
      setErrorMessage(
        error instanceof ApiError && error.status === 409
          ? 'Já existe uma reserva para este carregador nesse horário.'
          : 'Não foi possível criar a reserva. Confira o horário escolhido.'
      )
    },
  })

  const minDateTime = new Date(Date.now() + 5 * 60_000).toISOString().slice(0, 16)

  return (
    <div className="mt-3 flex flex-col gap-2 rounded-xl bg-cream p-3">
      <label className="text-xs font-semibold text-ink-soft">
        Horário de início
        <input
          type="datetime-local"
          value={start}
          min={minDateTime}
          onChange={(event) => setStart(event.target.value)}
          className="mt-1 w-full rounded-lg border border-hairline px-3 py-2 text-sm"
        />
      </label>
      <label className="text-xs font-semibold text-ink-soft">
        Duração
        <select
          value={durationMin}
          onChange={(event) => setDurationMin(Number(event.target.value))}
          className="mt-1 w-full rounded-lg border border-hairline px-3 py-2 text-sm"
        >
          <option value={30}>30 min</option>
          <option value={60}>1 hora</option>
          <option value={120}>2 horas</option>
        </select>
      </label>
      {errorMessage && <p className="text-xs text-status-problema">{errorMessage}</p>}
      <div className="flex gap-2">
        <Button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={!start || mutation.isPending}
          className="flex-1"
        >
          Confirmar
        </Button>
        <Button type="button" variant="secondary" onClick={onDone} className="flex-1">
          Cancelar
        </Button>
      </div>
    </div>
  )
}

// Simular o cartao num carregador especifico (Tarefa 3, escolha de vaga) - mesmo endpoint
// real (`POST /sessions/start`) do atalho generico da tela de Sessao, so que aqui o cliente
// ja escolheu a vaga exata em vez do backend pegar a primeira livre de qualquer
// estabelecimento. Ao suceder, navega pra Sessao pra acompanhar a sessao abrindo.
function SimulateRfidHereButton({ chargerId }) {
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: () => apiClient.post('/sessions/start', { charger_id: chargerId }),
    onSuccess: () => navigate('/'),
  })

  return (
    <div className="mt-2">
      <Button
        variant="secondary"
        className="w-full"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? 'Simulando leitura…' : '📶 Simular cartão RFID nesta vaga'}
      </Button>
      {mutation.isError && (
        <p className="mt-1.5 text-[11px] text-status-problema">
          {startSessionErrorMessage(mutation.error)}
        </p>
      )}
    </div>
  )
}

function ChargerCard({ charger, onJoinQueue, joinPending, reservingChargerId, setReservingChargerId }) {
  const secondsAgo = secondsSince(charger.latest_reading_at)

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-ink">{charger.spot_label}</p>
          <p className="text-xs text-muted-2">{charger.model}</p>
        </div>
        <StatusBadge status={charger.status} />
      </div>

      {secondsAgo != null && (
        <p className="mt-1 text-[11px] text-muted-3">
          {formatUpdatedAgo(secondsAgo)}
          {charger.status === 'carregando' &&
            charger.latest_power_kw != null &&
            ` · ${formatPowerKw(charger.latest_power_kw)}`}
        </p>
      )}

      {charger.status === 'livre' && reservingChargerId !== charger.id && (
        <>
          <div className="mt-3 flex gap-2">
            <Button onClick={() => onJoinQueue(charger)} disabled={joinPending} className="flex-1">
              Entrar na fila
            </Button>
            <Button
              variant="secondary"
              onClick={() => setReservingChargerId(charger.id)}
              className="flex-1"
            >
              Reservar horário
            </Button>
          </div>
          <SimulateRfidHereButton chargerId={charger.id} />
        </>
      )}

      {reservingChargerId === charger.id && (
        <ReservationForm chargerId={charger.id} onDone={() => setReservingChargerId(null)} />
      )}
    </Card>
  )
}

export function MapaDetalhePage() {
  const { establishmentId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [reservingChargerId, setReservingChargerId] = useState(null)
  const [joinError, setJoinError] = useState(null)

  const { data: establishments } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
  })
  const establishment = establishments?.find((item) => item.id === establishmentId)

  const { data: chargers, isLoading } = useQuery({
    queryKey: ['chargers-status', establishmentId],
    queryFn: () => apiClient.get(`/establishments/${establishmentId}/chargers-status`),
    refetchInterval: 20_000,
  })

  const { data: myReservations } = useQuery({
    queryKey: ['reservations-mine'],
    queryFn: () => apiClient.get('/reservations/mine'),
  })

  const chargerIds = useMemo(() => new Set((chargers ?? []).map((c) => c.id)), [chargers])
  const reservationsHere = (myReservations ?? []).filter(
    (reservation) => chargerIds.has(reservation.charger_id) && reservation.status === 'pending'
  )

  const joinMutation = useMutation({
    mutationFn: () => apiClient.post('/queue/join', { establishment_id: establishmentId }),
    onSuccess: () => navigate('/fila'),
    onError: (error) => {
      setJoinError(
        error instanceof ApiError && error.status === 409
          ? 'Você já está na fila ou tem uma sessão em andamento.'
          : 'Não foi possível entrar na fila agora.'
      )
    },
  })

  const cancelReservationMutation = useMutation({
    mutationFn: (reservationId) => apiClient.delete(`/reservations/${reservationId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reservations-mine'] }),
  })

  return (
    <div className="flex flex-1 flex-col">
      <div className="bg-ink-fixed px-5 pb-4 pt-[18px] text-white">
        <Link to="/mapa" className="text-xs text-white/70">
          ← Mapa
        </Link>
        <p className="mt-1 text-[15px] font-semibold">{establishment?.name ?? 'Estabelecimento'}</p>
      </div>

      <div className="flex flex-col gap-3 p-5">
        <Link
          to={`/mapa/${establishmentId}/planos`}
          className="flex items-center justify-between rounded-2xl bg-gradient-to-r from-brand to-brand-hover px-4 py-3.5 text-white shadow-[0_2px_14px_rgba(230,0,18,0.25)]"
        >
          <div>
            <p className="text-sm font-bold">Planos e economia</p>
            <p className="text-xs text-white/85">Até 25% de desconto na tarifa deste estabelecimento</p>
          </div>
          <span className="text-lg">→</span>
        </Link>

        {isLoading && (
          <>
            <Skeleton className="h-[200px] w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </>
        )}
        {!isLoading && chargers?.length > 0 && (
          <ChargersMiniMap establishment={establishment} chargers={chargers} />
        )}
        {joinError && <p className="text-xs text-status-problema">{joinError}</p>}

        {reservationsHere.length > 0 && (
          <Card>
            <p className="text-sm font-semibold text-ink">Suas reservas aqui</p>
            <div className="mt-2 flex flex-col gap-2">
              {reservationsHere.map((reservation) => {
                const charger = chargers?.find((c) => c.id === reservation.charger_id)
                return (
                  <div key={reservation.id} className="flex items-center justify-between text-xs text-ink-soft">
                    <span>
                      {charger?.spot_label} · {formatDateTime(reservation.scheduled_start)}
                    </span>
                    <button
                      type="button"
                      className="font-semibold text-status-problema"
                      onClick={() => cancelReservationMutation.mutate(reservation.id)}
                    >
                      Cancelar
                    </button>
                  </div>
                )
              })}
            </div>
          </Card>
        )}

        {chargers?.map((charger) => (
          <ChargerCard
            key={charger.id}
            charger={charger}
            onJoinQueue={() => joinMutation.mutate()}
            joinPending={joinMutation.isPending}
            reservingChargerId={reservingChargerId}
            setReservingChargerId={setReservingChargerId}
          />
        ))}

        {chargers?.length === 0 && <p className="text-sm text-muted">Nenhum carregador cadastrado.</p>}
      </div>
    </div>
  )
}
