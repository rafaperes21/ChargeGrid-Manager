export function RelatoriosPage() {
  const kpis = ['Receita no período', 'Sessões concluídas', 'Ticket médio', 'Energia total']

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[21px] font-bold text-ink">Relatórios</h1>
          <p className="mt-1 text-[13px] text-muted-2">Fechamento financeiro do período selecionado</p>
        </div>
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="grid grid-cols-4 gap-4">
          {kpis.map((label) => (
            <div key={label} className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
              <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
              <p className="mt-2 text-2xl font-bold text-muted-3">—</p>
            </div>
          ))}
        </div>

        <div className="rounded-[18px] border border-hairline bg-white p-[22px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <h2 className="mb-4 font-heading text-sm font-bold text-ink">Receita diária</h2>
          <div className="flex h-[180px] items-center justify-center rounded-xl bg-cream">
            <p className="text-sm text-muted">Sem sessões concluídas ainda — gráfico aparece assim que houver dado.</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 rounded-2xl border border-status-carregando bg-blue-50 px-[18px] py-[13px]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          <span className="text-[13px] text-blue-700">
            <strong>Em construção</strong> — relatórios financeiros dependem de sessões fechadas pelo
            motor de tarifação (M3), que ainda não foi implementado.
          </span>
        </div>
      </div>
    </div>
  )
}
