import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { formatCurrency, formatEnergyKwh } from '../lib/format'
import { animateNumber, MICRO, useGSAP } from '../lib/motion'

// Sugestao de cross-sell (Tarefa 5.2) - regra simples sobre dado real do proprio
// estabelecimento (nunca cruza dado de outro dono): quanto mais perto do limite de conexao
// contratada, maior o caso pra reduzir dependencia da rede com solar. Nao e uma analise de
// engenharia - so um sinal, explicitado como tal na propria tela.
function solarSuggestion(establishment) {
  const gridConnection = Number(establishment.grid_connection_kw)
  const powerLimit = Number(establishment.power_limit_kw)
  if (!gridConnection) return null

  const utilizationRatio = powerLimit / gridConnection
  if (utilizationRatio < 0.5) return null

  return {
    utilizationPct: Math.round(utilizationRatio * 100),
  }
}

function StatCard({ label, valueRef, staticValue, hint }) {
  return (
    <div className="rounded-[22px] border border-hairline bg-surface p-5 shadow-[0_4px_20px_rgba(14,10,26,0.05)]">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      {staticValue !== undefined ? (
        <p className="mt-1.5 font-heading text-[28px] font-bold text-ink">{staticValue}</p>
      ) : (
        <p ref={valueRef} className="mt-1.5 font-heading text-[28px] font-bold text-ink" />
      )}
      {hint && <p className="mt-1.5 text-[11px] text-muted-2">{hint}</p>}
    </div>
  )
}

export function FrotaPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['fleet-overview'],
    queryFn: () => apiClient.get('/fleet/overview'),
    refetchInterval: 30_000,
  })
  const { establishment } = useAuth()

  const kwhRef = useRef(null)
  const revenueRef = useRef(null)
  const prevRef = useRef({ kwh: null, revenue: null })

  // Contagem ascendente igual ao resto do produto (mesma funcao de motion.js) - nao inventa
  // transicao nova.
  useGSAP(() => {
    if (!data) return
    const targets = [
      [kwhRef, Number(data.total_kwh_managed), 'kwh', formatEnergyKwh],
      [revenueRef, Number(data.total_revenue_processed), 'revenue', formatCurrency],
    ]
    for (const [ref, to, key, formatter] of targets) {
      const from = prevRef.current[key] ?? to
      animateNumber(ref.current, { from, to, ...MICRO, formatter })
      prevRef.current[key] = to
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.total_kwh_managed, data?.total_revenue_processed])

  const suggestion = establishment ? solarSuggestion(establishment) : null

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[23px] font-bold text-ink">Visão de frota</h1>
        <p className="mt-1 text-[13px] text-muted-2">
          Dado agregado de todos os estabelecimentos da plataforma — pra fins de demonstração.
        </p>
      </div>

      <div className="flex flex-col gap-5 p-8">
        {isLoading && <p className="text-sm text-muted">Carregando…</p>}

        {data && (
          <>
            <p className="text-xs text-muted-2">
              Base de demonstração atual: {data.establishments_count} estabelecimento
              {data.establishments_count !== 1 ? 's' : ''} — os números abaixo refletem essa
              escala real, não uma projeção.
            </p>

            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Estabelecimentos" staticValue={data.establishments_count} />
              <StatCard label="Carregadores" staticValue={data.chargers_count} />
              <StatCard label="Sessões concluídas" staticValue={data.finished_sessions_count} />
              <StatCard label="kWh gerenciados" valueRef={kwhRef} />
              <StatCard label="Receita processada" valueRef={revenueRef} />
              <StatCard
                label="Anomalias detectadas pela IA"
                staticValue={data.anomalies_detected_count}
                hint={data.ia_unavailable ? 'IA indisponível ao computar este número' : undefined}
              />
            </div>

            {suggestion && establishment && (
              <div className="rounded-[18px] border border-accent-purple/30 bg-accent-purple/5 p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-accent-purple">
                  Oportunidade GoodWe
                </p>
                <p className="mt-2 text-sm text-ink">
                  <strong>{establishment.name}</strong> usa {suggestion.utilizationPct}% da conexão
                  de rede contratada ({Number(establishment.power_limit_kw)} kW de{' '}
                  {Number(establishment.grid_connection_kw)} kW) só com os carregadores. Um
                  inversor solar GoodWe reduziria essa dependência da rede.
                </p>
                <p className="mt-1.5 text-[11px] text-muted-2">
                  Sugestão baseada numa regra simples (uso da conexão contratada), não uma
                  análise de engenharia — serve como sinal, não como orçamento.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
