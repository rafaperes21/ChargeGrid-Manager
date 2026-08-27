import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'

function formatElapsedSince(isoString) {
  const elapsedMinutes = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 60_000))
  if (elapsedMinutes < 1) return 'agora mesmo'
  if (elapsedMinutes < 60) return `${elapsedMinutes} min`
  const hours = Math.floor(elapsedMinutes / 60)
  return `${hours}h ${elapsedMinutes % 60}min`
}

export function FilaProprietarioPage() {
  const { establishment } = useAuth()

  const { data: entries, isLoading } = useQuery({
    queryKey: ['queue', establishment?.id],
    queryFn: () => apiClient.get(`/queue?establishment_id=${establishment.id}`),
    enabled: Boolean(establishment),
    refetchInterval: 15_000,
  })

  const reservedCount = entries?.filter((e) => e.reserved_charger_id).length ?? 0

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[21px] font-bold text-ink">Fila</h1>
        <p className="mt-1 text-[13px] text-muted-2">Ordem de chegada por vaga desejada</p>
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="grid grid-cols-3 gap-4">
          {[
            ['Na fila agora', entries?.length ?? '—'],
            ['Tempo médio de espera', '—'],
            ['Reservas ativas (15 min)', entries ? reservedCount : '—'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
              <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
              <p className="mt-2 text-2xl font-bold text-muted-3">{value}</p>
            </div>
          ))}
        </div>

        <div className="overflow-hidden rounded-[18px] border border-hairline bg-white shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <div className="grid grid-cols-[60px_1.4fr_1fr_1fr_140px] bg-[#F4F2FB] px-[18px] py-3">
            <span className="text-[11px] font-bold text-muted">POS.</span>
            <span className="text-[11px] font-bold text-muted">USUÁRIO</span>
            <span className="text-[11px] font-bold text-muted">NA FILA HÁ</span>
            <span className="text-[11px] font-bold text-muted">ESPERA ESTIMADA</span>
            <span className="text-[11px] font-bold text-muted">AÇÃO</span>
          </div>

          {isLoading && <p className="px-[18px] py-8 text-center text-sm text-muted">Carregando…</p>}

          {entries?.length === 0 && (
            <p className="px-[18px] py-8 text-center text-sm text-muted">Nenhum cliente na fila no momento.</p>
          )}

          {entries?.map((entry, index) => (
            <div
              key={entry.id}
              className="grid grid-cols-[60px_1.4fr_1fr_1fr_140px] items-center border-t border-hairline px-[18px] py-3"
            >
              <span className="text-sm font-bold text-ink">{index + 1}</span>
              <span className="text-sm text-ink">{entry.user_full_name}</span>
              <span className="text-sm text-muted-2">{formatElapsedSince(entry.entered_at)}</span>
              <span className="text-sm text-muted-2">—</span>
              <span className="text-sm text-muted-2">
                {entry.reserved_charger_id ? (
                  <span className="rounded-full bg-status-reservado/10 px-2.5 py-1 text-[11px] font-semibold text-status-reservado">
                    Reservado
                  </span>
                ) : (
                  '—'
                )}
              </span>
            </div>
          ))}
        </div>

        <p className="text-[11px] text-muted">
          "Espera estimada" e "tempo médio de espera" dependem de um modelo de duração de sessão
          por carregador que ainda não existe — mostrar aqui seria inventar número.
        </p>
      </div>
    </div>
  )
}
