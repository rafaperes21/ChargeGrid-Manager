export function AjudaPage() {
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center gap-2.5 bg-ink px-5 py-4 text-white">
        <svg width="22" height="22" viewBox="0 0 24 24" className="shrink-0">
          <defs>
            <linearGradient id="cbolt3" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FF7A1A" />
              <stop offset="55%" stopColor="#E60012" />
              <stop offset="100%" stopColor="#7C3AED" />
            </linearGradient>
          </defs>
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" fill="url(#cbolt3)" />
        </svg>
        <div>
          <p className="font-heading text-sm font-semibold">Ajuda</p>
          <p className="mt-0.5 text-[10.5px] text-white/55">pergunte sobre sua sessão, tarifa ou plano</p>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3.5 p-5">
        <div className="max-w-[85%] self-start rounded-[16px_16px_16px_4px] bg-[#F7F5FB] px-[15px] py-[11px]">
          <p className="text-[13px] leading-relaxed text-ink">
            Esse assistente ainda está em construção — hoje só o assistente técnico do
            proprietário tem ferramentas reais conectadas. Em breve dá para perguntar sobre sua
            sessão, tarifa e fila por aqui também.
          </p>
        </div>
      </div>

      <div className="border-t border-hairline px-5 py-3">
        <div className="flex items-center gap-2 rounded-full border-[1.5px] border-[#E7E4F0] py-2 pl-4 pr-2">
          <span className="flex-1 text-[13px] text-muted-3">Escreva sua pergunta…</span>
          <button
            type="button"
            disabled
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand opacity-40"
            aria-label="Enviar"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
