import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../components/ui/Button'
import { apiClient } from '../lib/apiClient'

const MODEL_LABELS = { GW7K: 'GoodWe HCA G2 — GW7K', GW11K: 'GoodWe HCA G2 — GW11K', GW22K: 'GoodWe HCA G2 — GW22K' }

const DEFAULT_FORM = {
  available_power_kw: '40',
  phase: 'trifasico',
  parking_spots: '8',
  establishment_type: 'estacionamento',
}

async function downloadPdf(form, result) {
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF()

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(16)
  doc.text('ChargeGrid-Manager — Orçamento preliminar', 14, 18)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(11)
  let y = 32
  const line = (text) => {
    doc.text(text, 14, y)
    y += 8
  }

  line(`Modelo recomendado: ${MODEL_LABELS[result.recommended_model]}`)
  line(`Potência nominal: ${result.recommended_model_nominal_power_kw} kW`)
  line(`Corrente máxima por fase: ${result.recommended_model_max_current_a} A (TODO(datasheet) — confirmar BR)`)
  line(`Quantidade recomendada de pontos: ${result.max_chargers}`)
  line(`Potência disponível informada: ${form.available_power_kw} kW`)
  line(`Tipo de rede: ${form.phase === 'trifasico' ? 'Trifásica' : 'Monofásica'}`)
  line(`Vagas destinadas: ${form.parking_spots}`)
  y += 4
  line('Investimento e payback:')
  line(result.budget.note ?? `Capex estimado: R$ ${result.budget.capex}`)
  y += 8
  doc.setFontSize(9)
  doc.text(
    'Estimativa preliminar — não substitui projeto elétrico assinado por profissional habilitado (ART / NBR 5410 / NBR 17019).',
    14,
    y,
    { maxWidth: 180 },
  )

  doc.save('orcamento-chargegrid.pdf')
}

export function OnboardingPage() {
  const [form, setForm] = useState(DEFAULT_FORM)

  const mutation = useMutation({
    mutationFn: (payload) => apiClient.post('/onboarding/dimensionamento', payload),
  })

  function handleSubmit(event) {
    event.preventDefault()
    mutation.mutate({
      available_power_kw: form.available_power_kw,
      phase: form.phase,
      parking_spots: Number(form.parking_spots),
      establishment_type: form.establishment_type,
    })
  }

  const result = mutation.data

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[21px] font-bold text-ink">Onboarding — Dimensionamento</h1>
        <p className="mt-1 text-[13px] text-muted-2">
          Calculadora do carregador GoodWe HCA G2 ideal para o estabelecimento
        </p>
      </div>

      <div className="grid grid-cols-[420px_1fr] items-start gap-5 p-8">
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-[18px] rounded-[18px] border border-hairline bg-white p-6 shadow-[0_2px_14px_rgba(14,10,26,0.05)]"
        >
          <h2 className="font-heading text-sm font-bold text-ink">Dados da instalação</h2>

          <label className="flex flex-col gap-1.5 text-xs font-semibold text-muted-2">
            Potência disponível no padrão de entrada (kW)
            <input
              required
              type="number"
              step="0.1"
              value={form.available_power_kw}
              onChange={(e) => setForm({ ...form, available_power_kw: e.target.value })}
              className="rounded-xl border border-[#E7E7EA] px-3.5 py-2.5 text-sm font-normal text-ink"
            />
          </label>

          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted-2">Tipo de rede</p>
            <div className="flex gap-2">
              {[
                { value: 'trifasico', label: 'Trifásica 380V' },
                { value: 'monofasico', label: 'Monofásica 220V' },
              ].map((option) => (
                <button
                  type="button"
                  key={option.value}
                  onClick={() => setForm({ ...form, phase: option.value })}
                  className={`flex-1 rounded-xl border p-2.5 text-[13px] font-semibold ${
                    form.phase === option.value
                      ? 'border-brand bg-brand/5 text-brand'
                      : 'border-[#E7E7EA] text-muted-2'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex flex-col gap-1.5 text-xs font-semibold text-muted-2">
            Vagas destinadas ao carregamento
            <input
              required
              type="number"
              min="1"
              value={form.parking_spots}
              onChange={(e) => setForm({ ...form, parking_spots: e.target.value })}
              className="rounded-xl border border-[#E7E7EA] px-3.5 py-2.5 text-sm font-normal text-ink"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-semibold text-muted-2">
            Tipo de estabelecimento
            <select
              value={form.establishment_type}
              onChange={(e) => setForm({ ...form, establishment_type: e.target.value })}
              className="rounded-xl border border-[#E7E7EA] px-3.5 py-2.5 text-sm font-normal text-ink"
            >
              <option value="shopping">Shopping</option>
              <option value="estacionamento">Estacionamento</option>
              <option value="empresa">Empresa</option>
            </select>
          </label>

          <Button type="submit" className="mt-1.5" disabled={mutation.isPending}>
            {mutation.isPending ? 'Calculando…' : 'Recalcular recomendação'}
          </Button>
        </form>

        <div className="flex flex-col gap-4">
          {!result && !mutation.isPending && (
            <p className="text-sm text-muted">Preencha os dados e calcule a recomendação.</p>
          )}

          {result && (
            <>
              <div className="flex items-center justify-between rounded-[18px] border-[1.5px] border-brand bg-white p-6 shadow-[0_2px_14px_rgba(230,0,18,0.08)]">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-brand">Modelo recomendado</p>
                  <p className="mt-2 font-heading text-[26px] font-extrabold text-ink">
                    {MODEL_LABELS[result.recommended_model]}
                  </p>
                  <p className="mt-1 text-xs text-muted-2">
                    {result.recommended_model_nominal_power_kw} kW · atende{' '}
                    {result.max_chargers > 0 ? `${result.max_chargers} vagas` : 'nenhuma vaga com a carga informada'}
                  </p>
                  {result.max_chargers === 0 && result.min_power_required_kw && (
                    <p className="mt-1 text-xs text-status-problema">
                      Carga mínima necessária para 1 ponto: {result.min_power_required_kw} kW
                    </p>
                  )}
                </div>
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-ink">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="#E60012">
                    <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
                  </svg>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Investimento estimado</p>
                  <p className="mt-2 text-[22px] font-bold text-ink">
                    {result.budget.capex ? `R$ ${Number(result.budget.capex).toFixed(0)}` : 'Sob consulta'}
                  </p>
                  <p className="mt-1.5 text-[11px] text-muted">TODO(datasheet) — preço a confirmar</p>
                </div>
                <div className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Payback estimado</p>
                  <p className="mt-2 text-[22px] font-bold text-ink">
                    {result.budget.payback_months ? `${Number(result.budget.payback_months).toFixed(0)} meses` : 'Sob consulta'}
                  </p>
                  <p className="mt-1.5 text-[11px] text-muted">
                    {result.budget.note ?? 'com ocupação estimada'}
                  </p>
                </div>
                <div className="rounded-[18px] border border-hairline bg-white p-[18px] shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-muted">Corrente máxima por fase</p>
                  <p className="mt-2 text-[22px] font-bold text-ink">{result.recommended_model_max_current_a} A</p>
                  <p className="mt-1.5 text-[11px] text-muted">TODO(datasheet) — confirmar BR</p>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-[18px] border border-hairline bg-white p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
                <div>
                  <p className="text-[13px] font-semibold text-ink">Orçamento completo em PDF</p>
                  <p className="mt-1 text-xs text-muted">
                    Modelo, payback, condições de instalação e observações do datasheet
                  </p>
                </div>
                <Button variant="secondary" onClick={() => downloadPdf(form, result)}>
                  Gerar PDF
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
