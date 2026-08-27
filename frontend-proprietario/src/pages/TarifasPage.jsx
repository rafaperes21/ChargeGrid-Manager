import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Button } from '../components/ui/Button'
import { ApiError, apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { gsap, TRANSITION, useGSAP } from '../lib/motion'

const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

const PAYMENT_METHOD_LABELS = {
  pix: 'Pix',
  cartao_credito: 'Cartão de crédito',
  cartao_debito: 'Cartão de débito',
  carteira_do_app: 'Carteira do app',
}

// Declarativo (M3, Tarefa 4.2): so define o que aparece pro cliente escolher ao fechar a
// sessao (Tarefa 4.3) - nunca processa pagamento de verdade.
function PaymentMethodsSettings({ establishmentId }) {
  const queryClient = useQueryClient()

  const { data: establishment } = useQuery({
    queryKey: ['establishment', establishmentId],
    queryFn: () => apiClient.get(`/establishments/${establishmentId}`),
    enabled: Boolean(establishmentId),
  })

  const updateMutation = useMutation({
    mutationFn: (accepted_payment_methods) =>
      apiClient.patch(`/establishments/${establishmentId}`, { accepted_payment_methods }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['establishment', establishmentId] }),
  })

  if (!establishment) return null

  const accepted = establishment.accepted_payment_methods ?? []

  function toggle(method) {
    const next = accepted.includes(method)
      ? accepted.filter((m) => m !== method)
      : [...accepted, method]
    updateMutation.mutate(next)
  }

  return (
    <div className="rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
      <h2 className="font-heading text-sm font-bold text-ink">Formas de pagamento aceitas</h2>
      <p className="mt-1 text-xs text-muted-2">
        O cliente escolhe entre essas opções ao fechar a sessão — apenas registra a escolha,
        não processa pagamento de verdade.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(PAYMENT_METHOD_LABELS).map(([method, label]) => {
          const active = accepted.includes(method)
          return (
            <button
              type="button"
              key={method}
              disabled={updateMutation.isPending}
              onClick={() => toggle(method)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${
                active ? 'bg-brand text-white' : 'border border-hairline text-muted-2'
              }`}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function PricingSuggestions({ establishmentId }) {
  const queryClient = useQueryClient()
  const [appliedId, setAppliedId] = useState(null)
  const cardsRef = useRef(null)

  const { data, isLoading } = useQuery({
    queryKey: ['pricing-suggestions', establishmentId],
    queryFn: () => apiClient.get(`/pricing-suggestions/establishments/${establishmentId}`),
    enabled: Boolean(establishmentId),
    refetchInterval: 60_000,
  })

  // Entrada com leve slide+fade a cada vez que a lista de sugestoes muda (novo horizonte,
  // sugestao aplicada e removida, etc.) - gsap.set() garante o estado inicial sincrono
  // (ver feedback_gsap_counter_gotcha: sem isso, gsap.fromTo() com o mesmo from/to nunca
  // dispara onUpdate e o card fica sem transicao visivel).
  useGSAP(() => {
    if (!cardsRef.current) return
    const cards = cardsRef.current.querySelectorAll('[data-suggestion-card]')
    if (cards.length === 0) return
    gsap.set(cards, { autoAlpha: 0, y: 8 })
    gsap.to(cards, { autoAlpha: 1, y: 0, stagger: 0.06, ...TRANSITION })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.suggestions?.length])

  const applyMutation = useMutation({
    mutationFn: ({ tariffRuleId, price }) =>
      apiClient.patch(`/tariffs/${tariffRuleId}`, { price_per_kwh: price }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tariffs', establishmentId] })
      setAppliedId(variables.tariffRuleId)
    },
  })

  if (isLoading || !data) return null

  if (data.status === 'insufficient_data') {
    return (
      <div className="rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
        <h2 className="font-heading text-sm font-bold text-ink">Sugestão de precificação dinâmica</h2>
        <p className="mt-2 text-sm text-muted">
          Ainda não há histórico suficiente (mínimo de semanas de dado) para a IA sugerir ajustes.
        </p>
      </div>
    )
  }

  if (data.status === 'ia_unavailable') {
    return (
      <div className="rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
        <h2 className="font-heading text-sm font-bold text-ink">Sugestão de precificação dinâmica</h2>
        <p className="mt-2 text-sm text-status-problema">Serviço de IA indisponível no momento.</p>
      </div>
    )
  }

  return (
    <div className="rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
      <h2 className="font-heading text-sm font-bold text-ink">Sugestão de precificação dinâmica</h2>
      <p className="mt-1 text-xs text-muted-2">
        A IA nunca altera tarifa sozinha — cada sugestão só vale se você clicar em "Aplicar".
      </p>

      {data.suggestions.length === 0 && (
        <p className="mt-3 text-sm text-muted">Nenhum ajuste sugerido pro horizonte atual.</p>
      )}

      <div ref={cardsRef} className="mt-3 flex flex-col gap-2.5">
        {data.suggestions.map((s) => {
          const key = `${s.tariff_rule_id}-${s.day_of_week}-${s.hour_local}`
          const isIncrease = s.direction === 'increase'
          const wasApplied = appliedId === s.tariff_rule_id && applyMutation.isSuccess
          return (
            <div
              key={key}
              data-suggestion-card
              className="flex items-center justify-between gap-3 rounded-2xl border border-hairline px-4 py-3"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      isIncrease ? 'bg-status-reservado/10 text-status-reservado' : 'bg-status-carregando/10 text-status-carregando'
                    }`}
                  >
                    {isIncrease ? '↑ Aumento' : '↓ Redução'}
                  </span>
                  <span className="text-xs font-semibold text-muted-2">
                    {DAY_LABELS[s.day_of_week]} {s.hour_local}h · {s.tariff_rule_name}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">{s.reason}</p>
                <p className="mt-1 text-sm text-ink">
                  R$ {Number(s.current_price_per_kwh).toFixed(2)} →{' '}
                  <strong>R$ {Number(s.suggested_price_per_kwh).toFixed(2)}</strong>/kWh
                </p>
              </div>
              <Button
                variant="ghost"
                disabled={applyMutation.isPending}
                onClick={() =>
                  applyMutation.mutate({
                    tariffRuleId: s.tariff_rule_id,
                    price: String(s.suggested_price_per_kwh),
                  })
                }
              >
                {wasApplied ? 'Aplicado ✓' : 'Aplicar'}
              </Button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function describeDays(daysOfWeek) {
  const days = daysOfWeek.split(',').filter(Boolean).map(Number).sort()
  if (days.length === 5 && days.every((d, i) => d === i)) return 'Segunda a sexta'
  if (days.length === 2 && days.includes(5) && days.includes(6)) return 'Sábado e domingo'
  if (days.length === 7) return 'Todos os dias'
  return days.map((d) => DAY_LABELS[d]).join(', ')
}

const EMPTY_FORM = {
  name: '',
  days_of_week: '0,1,2,3,4',
  start_time_local: '18:00',
  end_time_local: '21:00',
  price_per_kwh: '',
  is_special: false,
}

export function TarifasPage() {
  const { establishment } = useAuth()
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [formError, setFormError] = useState(null)
  const [showForm, setShowForm] = useState(false)

  const { data: rules, isLoading } = useQuery({
    queryKey: ['tariffs', establishment?.id],
    queryFn: () => apiClient.get(`/tariffs?establishment_id=${establishment.id}`),
    enabled: Boolean(establishment),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['tariffs', establishment?.id] })

  const createMutation = useMutation({
    mutationFn: (payload) => apiClient.post('/tariffs', payload),
    onSuccess: () => {
      invalidate()
      setForm(EMPTY_FORM)
      setShowForm(false)
      setFormError(null)
    },
    onError: (error) => setFormError(errorMessage(error)),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => apiClient.patch(`/tariffs/${id}`, payload),
    onSuccess: () => {
      invalidate()
      setEditingId(null)
      setForm(EMPTY_FORM)
      setShowForm(false)
      setFormError(null)
    },
    onError: (error) => setFormError(errorMessage(error)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => apiClient.delete(`/tariffs/${id}`),
    onSuccess: invalidate,
  })

  function errorMessage(error) {
    if (error instanceof ApiError && error.status === 409) {
      return 'Essa faixa se sobrepõe a uma faixa existente no mesmo dia.'
    }
    return 'Não foi possível salvar a tarifa.'
  }

  function handleSubmit(event) {
    event.preventDefault()
    const payload = { ...form, price_per_kwh: form.price_per_kwh }
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload })
    } else {
      createMutation.mutate({ ...payload, establishment_id: establishment.id })
    }
  }

  function startEdit(rule) {
    setEditingId(rule.id)
    setForm({
      name: rule.name,
      days_of_week: rule.days_of_week,
      start_time_local: rule.start_time_local.slice(0, 5),
      end_time_local: rule.end_time_local.slice(0, 5),
      price_per_kwh: String(rule.price_per_kwh),
      is_special: rule.is_special,
    })
    setShowForm(true)
    setFormError(null)
  }

  if (!establishment) return null

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[21px] font-bold text-ink">Tarifas</h1>
          <p className="mt-1 text-[13px] text-muted-2">
            Faixas de preço por horário local (America/Sao_Paulo)
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingId(null)
            setForm(EMPTY_FORM)
            setFormError(null)
            setShowForm((v) => !v)
          }}
        >
          + Nova tarifa
        </Button>
      </div>

      <div className="flex flex-col gap-4 p-8">
        <PricingSuggestions establishmentId={establishment.id} />
        <PaymentMethodsSettings establishmentId={establishment.id} />

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-3 rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]"
          >
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Nome
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Preço por kWh (R$)
                <input
                  required
                  type="number"
                  step="0.0001"
                  value={form.price_per_kwh}
                  onChange={(e) => setForm({ ...form, price_per_kwh: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Início
                <input
                  required
                  type="time"
                  value={form.start_time_local}
                  onChange={(e) => setForm({ ...form, start_time_local: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Fim
                <input
                  required
                  type="time"
                  value={form.end_time_local}
                  onChange={(e) => setForm({ ...form, end_time_local: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {DAY_LABELS.map((label, index) => {
                const days = form.days_of_week.split(',').filter(Boolean).map(Number)
                const active = days.includes(index)
                return (
                  <button
                    type="button"
                    key={label}
                    onClick={() => {
                      const next = active ? days.filter((d) => d !== index) : [...days, index]
                      setForm({ ...form, days_of_week: next.sort().join(',') })
                    }}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      active ? 'bg-brand text-white' : 'border border-hairline text-muted-2'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-2">
              <input
                type="checkbox"
                checked={form.is_special}
                onChange={(e) => setForm({ ...form, is_special: e.target.checked })}
              />
              Faixa especial (feriado, evento)
            </label>
            {formError && <p className="text-sm text-status-problema">{formError}</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Salvar alterações' : 'Criar tarifa'}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
            </div>
          </form>
        )}

        {isLoading && <p className="text-sm text-muted">Carregando…</p>}

        {rules?.length === 0 && !isLoading && (
          <p className="text-sm text-muted">Nenhuma faixa de tarifa cadastrada ainda.</p>
        )}

        {rules?.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center justify-between rounded-[18px] border border-hairline bg-surface p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]"
          >
            <div className="flex items-center gap-4">
              <span
                className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
                  rule.is_special ? 'bg-brand/10 text-brand' : 'bg-[#F4F2FB] text-muted-2'
                }`}
              >
                {rule.is_special ? 'Especial' : 'Padrão'}
              </span>
              <div>
                <p className="text-sm font-semibold text-ink">
                  {describeDays(rule.days_of_week)} · {rule.start_time_local.slice(0, 5)}–
                  {rule.end_time_local.slice(0, 5)}
                </p>
                <p className="mt-0.5 text-xs text-muted">{rule.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <p className="text-lg font-bold text-ink">
                R$ {Number(rule.price_per_kwh).toFixed(2)}
                <span className="text-xs font-medium text-muted">/kWh</span>
              </p>
              <button
                type="button"
                onClick={() => startEdit(rule)}
                className="text-muted hover:text-ink"
                aria-label="Editar"
              >
                ✎
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(rule.id)}
                className="text-muted hover:text-status-problema"
                aria-label="Excluir"
              >
                ✕
              </button>
            </div>
          </div>
        ))}

        <p className="mt-1 text-[11px] text-muted">
          Preço sempre em Decimal, com 4 casas na base — exibido aqui com 2 casas por
          convenção monetária pt-BR.
        </p>
      </div>
    </div>
  )
}
