export function FilaPage() {
  return (
    <div className="flex flex-1 flex-col items-center gap-5 px-5 pb-5 pt-9">
      <div className="relative h-[160px] w-[160px]">
        <svg width="160" height="160" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="76" fill="none" stroke="#EAE6F2" strokeWidth="14" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-2">Posição</span>
          <span className="text-4xl font-extrabold text-muted-3">—</span>
        </div>
      </div>

      <p className="text-center text-sm text-muted-2">Você não está na fila de nenhum estacionamento no momento.</p>

      <div className="flex w-full items-center gap-2.5 rounded-2xl border border-status-carregando bg-blue-50 px-4 py-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <span className="text-xs text-blue-700">
          <strong>Em construção</strong> — a fila depende do motor de tarifação/sessões (M3).
        </span>
      </div>
    </div>
  )
}
