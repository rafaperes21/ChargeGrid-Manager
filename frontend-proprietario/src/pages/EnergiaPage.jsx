import { useQuery } from '@tanstack/react-query'
import { EnergyDayChart } from '../components/energy/EnergyDayChart'
import { EnergyFlowDiagram } from '../components/energy/EnergyFlowDiagram'
import { Skeleton } from '../components/ui/Skeleton'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { formatEnergyKwh, formatPowerKw, formatUpdatedAgo } from '../lib/format'

// Fluxo de energia do estabelecimento (Sprint 4): inversor solar e bateria GoodWe simulados,
// despacho solar -> bateria -> rede feito pelo backend a cada tick do polling. Tudo aqui vem
// de GET /establishments/{id}/energy/flow - nenhum numero e calculado ou estimado na tela.
function Kpi({ label, value, hint }) {
  return (
    <div className="flex flex-col justify-center rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1.5 font-heading text-[26px] font-bold text-ink">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-muted-2">{hint}</p>}
    </div>
  )
}

function secondsSince(iso) {
  return (Date.now() - new Date(iso).getTime()) / 1000
}

export function EnergiaPage() {
  const { establishment } = useAuth()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['energy-flow', establishment?.id],
    queryFn: () => apiClient.get(`/establishments/${establishment.id}/energy/flow`),
    enabled: Boolean(establishment),
    refetchInterval: 20_000,
  })

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[23px] font-bold text-ink">Fluxo de energia</h1>
          <p className="mt-1 text-[13px] text-muted-2">
            Prioridade de despacho: solar → bateria → rede, dentro do limite contratado
          </p>
        </div>
        <span className="rounded-full bg-status-reservado/10 px-3 py-1 text-[11px] font-semibold text-status-reservado">
          Solar e bateria simulados
        </span>
      </div>

      <div className="flex flex-col gap-5 p-8">
        {isLoading && (
          <>
            <Skeleton className="h-[300px] w-full rounded-[22px]" />
            <Skeleton className="h-[120px] w-full rounded-[22px]" />
          </>
        )}
        {isError && <p className="text-sm text-status-problema">Não foi possível carregar o fluxo de energia agora.</p>}
        {data && <EnergyContent data={data} />}
      </div>
    </div>
  )
}

function EnergyContent({ data }) {
  const { latest, today, battery, inverter, series } = data
  const share = today.renewable_share_pct

  return (
    <>
      <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-heading text-base font-semibold text-ink">Agora</h2>
          {latest && (
            <span className="flex items-center gap-1.5 font-mono text-[11px] text-muted">
              <span className="cgm-pulse inline-block h-1.5 w-1.5 rounded-full bg-brand" />
              {formatUpdatedAgo(secondsSince(latest.timestamp))}
            </span>
          )}
        </div>
        {latest ? (
          <>
            <EnergyFlowDiagram point={latest} socPct={latest.battery_soc_pct} />
            {Number(latest.demand_limited_kw) > 0 && (
              <p className="mt-2 rounded-xl bg-status-reservado/10 px-3 py-2 text-xs text-ink-soft">
                Controle de demanda ativo: {formatPowerKw(latest.demand_limited_kw)} a menos que o nominal pedido
                pelos carregadores, para não passar de {formatPowerKw(latest.grid_limit_kw)} na rede.
              </p>
            )}
          </>
        ) : (
          <div className="flex h-[200px] flex-col items-center justify-center gap-1.5 rounded-2xl border border-dashed border-hairline text-center">
            <p className="text-sm font-semibold text-ink-soft">Nenhuma leitura de fluxo ainda</p>
            <p className="max-w-[340px] text-xs text-muted-2">
              O worker de polling (<code>python -m app.integracoes.polling</code>) grava uma leitura a cada ciclo — suba
              ele com <code>./scripts/dev.sh</code>.
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label="Renovável hoje"
          value={share === null ? '—' : `${Number(share).toLocaleString('pt-BR')}%`}
          hint="da energia entregue aos carros (solar + bateria)"
        />
        <Kpi label="Solar gerado hoje" value={formatEnergyKwh(today.solar_generated_kwh)} hint={`excedente ${formatEnergyKwh(today.solar_surplus_kwh)}`} />
        <Kpi label="Rede hoje" value={formatEnergyKwh(today.grid_to_load_kwh)} hint={`pico ${formatPowerKw(today.peak_grid_kw)}`} />
        <Kpi
          label="Bateria"
          value={latest?.battery_soc_pct != null ? `${Number(latest.battery_soc_pct).toFixed(0)}%` : '—'}
          hint={battery ? `${Number(battery.capacity_kwh).toLocaleString('pt-BR')} kWh · entregou ${formatEnergyKwh(today.battery_to_load_kwh)} hoje` : 'sem bateria cadastrada'}
        />
      </div>

      <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
        <h2 className="mb-3 font-heading text-base font-semibold text-ink">Hoje, por fonte</h2>
        <EnergyDayChart series={series} gridLimitKw={latest?.grid_limit_kw ?? 0} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <AssetCard
          title="Inversor solar"
          asset={inverter}
          lines={inverter ? [`${Number(inverter.rated_kw).toLocaleString('pt-BR')} kWp instalados`] : []}
        />
        <AssetCard
          title="Bateria"
          asset={battery}
          lines={
            battery
              ? [
                  `${Number(battery.capacity_kwh).toLocaleString('pt-BR')} kWh de capacidade`,
                  `carga/descarga até ${Number(battery.max_charge_kw).toLocaleString('pt-BR')} / ${Number(battery.max_discharge_kw).toLocaleString('pt-BR')} kW`,
                  `SoC mínimo ${Number(battery.min_soc_pct).toFixed(0)}% (protege a vida útil)`,
                ]
              : []
          }
        />
      </div>
      <p className="text-[11px] text-muted">
        Dados simulados: a geração solar e a bateria vêm do simulador de hardware (mesma interface que o SEMS+ real
        usaria), com premissas de dimensionamento — não são medições de um equipamento instalado.
      </p>
    </>
  )
}

function AssetCard({ title, asset, lines }) {
  return (
    <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{title}</p>
      {asset ? (
        <>
          <p className="mt-1.5 text-sm font-semibold text-ink">{asset.model}</p>
          <p className="font-mono text-[11px] text-muted-2">{asset.sems_serial}</p>
          <ul className="mt-2 space-y-0.5 text-xs text-ink-soft">
            {lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-1.5 text-sm text-muted">Não cadastrado neste estabelecimento.</p>
      )}
    </div>
  )
}
