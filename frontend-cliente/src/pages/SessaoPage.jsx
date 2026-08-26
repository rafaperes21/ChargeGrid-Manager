export function SessaoPage() {
  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <div className="flex items-center gap-2.5 rounded-2xl border border-status-carregando bg-blue-50 px-4 py-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <span className="text-xs text-blue-700">
          <strong>Em construção</strong> — depende de sessões reais do motor de tarifação (M3).
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-muted-3/10 px-3 py-1.5 text-xs font-medium text-muted-2">
          Nenhuma sessão ativa
        </span>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-2">Valor acumulado</p>
        <p className="mt-1 font-heading text-5xl font-bold leading-none text-muted-3">R$ —</p>
      </div>

      <div className="rounded-2xl border border-hairline bg-emerald-50 px-4 py-3">
        <p className="text-xs text-emerald-800">
          Aproxime seu cartão RFID de um carregador livre para iniciar uma sessão.
        </p>
      </div>
    </div>
  )
}
