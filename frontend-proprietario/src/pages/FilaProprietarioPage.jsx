export function FilaProprietarioPage() {
  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[21px] font-bold text-ink">Fila</h1>
        <p className="mt-1 text-[13px] text-muted-2">Ordem de chegada por vaga desejada</p>
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="grid grid-cols-3 gap-4">
          {['Na fila agora', 'Tempo médio de espera', 'Reservas ativas (15 min)'].map((label) => (
            <div key={label} className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
              <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
              <p className="mt-2 text-2xl font-bold text-muted-3">—</p>
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
          <p className="px-[18px] py-8 text-center text-sm text-muted">Nenhum cliente na fila no momento.</p>
        </div>

        <div className="flex items-center gap-2.5 rounded-2xl border border-status-carregando bg-blue-50 px-[18px] py-[13px]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          <span className="text-[13px] text-blue-700">
            <strong>Em construção</strong> — a fila é populada por sessões de carregamento reais, e o
            motor de tarifação/sessões (M3) ainda não foi implementado. A tela já está pronta, só
            falta o dado.
          </span>
        </div>
      </div>
    </div>
  )
}
