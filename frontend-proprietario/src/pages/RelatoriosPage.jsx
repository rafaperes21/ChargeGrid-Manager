import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { formatCurrency, formatEnergyKwh } from '../lib/format'

// Ocupacao por vaga: uma cor so (mesma marca do resto do produto) - e uma serie unica
// (receita) atravessada por categoria (vaga), nao uma comparacao de identidades diferentes,
// entao nao faz sentido uma cor por barra (skill dataviz: cor segue a entidade, nao o
// ranking). Poucas barras (uma por carregador) -> rotulo direto em vez de eixo/legenda.
function OccupancyChart({ chargers }) {
  const maxRevenue = Math.max(1, ...chargers.map((charger) => Number(charger.revenue)))

  return (
    <div className="flex h-[190px] items-end gap-4">
      {chargers.map((charger) => (
        <div key={charger.charger_id} className="flex flex-1 flex-col items-center gap-1.5">
          <span className="text-xs font-semibold text-ink">{formatCurrency(charger.revenue)}</span>
          <div
            className="w-full max-w-[64px] rounded-t-md bg-brand/80"
            style={{ height: `${Math.max(4, (Number(charger.revenue) / maxRevenue) * 130)}px` }}
            title={`${charger.spot_label}: ${formatCurrency(charger.revenue)} · ${formatEnergyKwh(charger.energy_kwh)} · ${charger.hours_charged}h`}
          />
          <span className="text-[11px] font-semibold text-ink-soft">{charger.spot_label}</span>
          <span className="text-[10px] text-muted-2">
            {charger.sessions_count} {charger.sessions_count === 1 ? 'sessão' : 'sessões'}
          </span>
        </div>
      ))}
    </div>
  )
}

export function RelatoriosPage() {
  const { establishment } = useAuth()

  const { data: report, isLoading } = useQuery({
    queryKey: ['reports', establishment?.id],
    queryFn: () => apiClient.get(`/establishments/${establishment.id}/reports`),
    enabled: Boolean(establishment),
  })

  const { data: occupancy, isLoading: isLoadingOccupancy } = useQuery({
    queryKey: ['chargers-occupancy', establishment?.id],
    queryFn: () => apiClient.get(`/establishments/${establishment.id}/chargers-occupancy`),
    enabled: Boolean(establishment),
  })

  const kpis = [
    ['Receita no período', report ? formatCurrency(report.revenue_total) : null],
    ['Sessões concluídas', report ? String(report.completed_sessions_count) : null],
    ['Ticket médio', report?.average_ticket !== null && report ? formatCurrency(report.average_ticket) : null],
    ['Energia total', report ? formatEnergyKwh(report.total_energy_kwh) : null],
  ]

  const maxDailyRevenue = Math.max(1, ...(report?.daily_revenue.map((d) => Number(d.revenue)) ?? [0]))

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[21px] font-bold text-ink">Relatórios</h1>
          <p className="mt-1 text-[13px] text-muted-2">
            {report
              ? `Fechamento financeiro de ${report.from_date} a ${report.to_date}`
              : 'Fechamento financeiro do período selecionado'}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="grid grid-cols-4 gap-4">
          {kpis.map(([label, value]) => (
            <div key={label} className="rounded-[18px] border border-hairline bg-surface p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
              <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
              <p className="mt-2 text-2xl font-bold text-ink">
                {isLoading ? '—' : (value ?? '—')}
              </p>
            </div>
          ))}
        </div>

        <div className="rounded-[18px] border border-hairline bg-surface p-[22px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <h2 className="mb-4 font-heading text-sm font-bold text-ink">Receita diária</h2>
          {report?.daily_revenue.length ? (
            <div className="flex h-[180px] items-end gap-1.5">
              {report.daily_revenue.map((point) => (
                <div key={point.date} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t-md bg-brand/80"
                    style={{ height: `${Math.max(4, (Number(point.revenue) / maxDailyRevenue) * 150)}px` }}
                    title={`${point.date}: ${formatCurrency(point.revenue)}`}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-[180px] items-center justify-center rounded-xl bg-cream">
              <p className="text-sm text-muted">
                {isLoading
                  ? 'Carregando…'
                  : 'Sem sessões concluídas ainda — gráfico aparece assim que houver dado.'}
              </p>
            </div>
          )}
        </div>

        <div className="rounded-[18px] border border-hairline bg-surface p-[22px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <h2 className="mb-1 font-heading text-sm font-bold text-ink">Ocupação por vaga</h2>
          <p className="mb-4 text-[11px] text-muted-2">receita e sessões concluídas no período, por carregador</p>
          {occupancy?.chargers.length ? (
            <OccupancyChart chargers={occupancy.chargers} />
          ) : (
            <div className="flex h-[190px] items-center justify-center rounded-xl bg-cream">
              <p className="text-sm text-muted">
                {isLoadingOccupancy ? 'Carregando…' : 'Nenhum carregador cadastrado ainda.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
