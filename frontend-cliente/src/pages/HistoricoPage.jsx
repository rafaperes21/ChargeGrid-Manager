export function HistoricoPage() {
  return (
    <div className="flex flex-1 flex-col gap-5 p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">Histórico</p>

      <div className="flex flex-col items-center gap-3 rounded-2xl border border-hairline p-8 text-center">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#9A96A6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 3v5h5" />
          <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
          <path d="M12 7v5l4 2" />
        </svg>
        <p className="text-sm text-muted-2">Nenhuma sessão concluída ainda.</p>
      </div>

      <div className="flex items-center gap-2.5 rounded-2xl border border-status-carregando bg-blue-50 px-4 py-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <span className="text-xs text-blue-700">
          <strong>Em construção</strong> — recibos e extrato dependem do motor de tarifação (M3).
        </span>
      </div>
    </div>
  )
}
