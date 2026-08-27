import { FaqAccordion } from '../components/ui/FaqAccordion'
import { SETTINGS_FAQ, SUPPORT_CONTACT } from '../lib/faq'

// Aba de configuracoes com FAQ tecnico estatico - ideia registrada no CLAUDE.md
// ("Ideias registradas, nao priorizadas ainda"), implementada por pedido explicito do
// usuario em 27/08/2026. Declarativo como o resto do suporte do projeto: o canal existe
// como dado na tela, ainda nao operacionalizado de verdade (ver SUPPORT_CONTACT).
export function ConfiguracoesPage() {
  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[21px] font-bold text-ink">Configurações</h1>
        <p className="mt-1 text-[13px] text-muted-2">
          FAQ técnico sobre tarifação, precificação sugerida e planos
        </p>
      </div>

      <div className="flex flex-col gap-5 p-8">
        <div className="rounded-[18px] border border-hairline bg-surface p-[22px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <h2 className="mb-3 font-heading text-sm font-bold text-ink">Perguntas frequentes</h2>
          <FaqAccordion items={SETTINGS_FAQ} />
        </div>

        <div className="rounded-[18px] border border-hairline bg-surface p-[22px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
          <h2 className="mb-3 font-heading text-sm font-bold text-ink">Suporte da plataforma</h2>
          <p className="text-xs text-muted-2">
            {SUPPORT_CONTACT.email} · {SUPPORT_CONTACT.phone}
          </p>
          <p className="mt-1 text-[11px] text-muted-3">({SUPPORT_CONTACT.note})</p>
        </div>
      </div>
    </div>
  )
}
