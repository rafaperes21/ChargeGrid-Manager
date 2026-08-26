import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../components/ui/Button'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'

const PLAN_KIND_LABELS = { avulso: 'Avulso', mensal: 'Mensal', trimestral: 'Trimestral' }

const EMPTY_PLAN_FORM = {
  name: '',
  kind: 'mensal',
  price: '',
  free_kwh_allowance: '',
  discount_pct: '',
  priority: 1,
}

export function UsuariosPlanosPage() {
  const { establishment } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_PLAN_FORM)

  const { data: plans } = useQuery({
    queryKey: ['plans', establishment?.id],
    queryFn: () => apiClient.get(`/plans?establishment_id=${establishment.id}`),
    enabled: Boolean(establishment),
  })

  const { data: users } = useQuery({
    queryKey: ['customers'],
    queryFn: () => apiClient.get('/users'),
  })

  const createPlanMutation = useMutation({
    mutationFn: (payload) => apiClient.post('/plans', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans', establishment?.id] })
      setForm(EMPTY_PLAN_FORM)
      setShowForm(false)
    },
  })

  const toggleBlockedMutation = useMutation({
    mutationFn: ({ id, blocked }) => apiClient.patch(`/users/${id}`, { blocked }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers'] }),
  })

  function handleSubmit(event) {
    event.preventDefault()
    createPlanMutation.mutate({
      establishment_id: establishment.id,
      name: form.name,
      kind: form.kind,
      price: form.price || null,
      free_kwh_allowance: form.free_kwh_allowance || null,
      discount_pct: form.discount_pct || null,
      priority: Number(form.priority),
    })
  }

  if (!establishment) return null

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-8 pt-7">
        <div>
          <h1 className="font-heading text-[21px] font-bold text-ink">Usuários e planos</h1>
          <p className="mt-1 text-[13px] text-muted-2">Cartões RFID cadastrados e planos de assinatura</p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>+ Novo plano</Button>
      </div>

      <div className="flex flex-col gap-6 p-8">
        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-3 rounded-[18px] border border-hairline bg-white p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]"
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
                Tipo
                <select
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                >
                  <option value="avulso">Avulso</option>
                  <option value="mensal">Mensal</option>
                  <option value="trimestral">Trimestral</option>
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Mensalidade (R$)
                <input
                  type="number"
                  step="0.01"
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-muted-2">
                Desconto (%)
                <input
                  type="number"
                  step="0.01"
                  value={form.discount_pct}
                  onChange={(e) => setForm({ ...form, discount_pct: e.target.value })}
                  className="rounded-md border border-hairline px-3 py-2 text-sm"
                />
              </label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={createPlanMutation.isPending}>
                Criar plano
              </Button>
              <Button variant="ghost" type="button" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
            </div>
          </form>
        )}

        <div>
          <h2 className="mb-3 font-heading text-[15px] font-bold text-ink">Planos</h2>
          <div className="grid grid-cols-3 gap-4">
            {plans?.map((plan) => (
              <div
                key={plan.id}
                className="rounded-[18px] border border-hairline bg-white p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)]"
              >
                <p className="text-xs font-bold uppercase tracking-wide text-muted">
                  {PLAN_KIND_LABELS[plan.kind]}
                </p>
                <p className="mt-2 text-2xl font-bold text-ink">
                  {plan.price ? `R$ ${Number(plan.price).toFixed(2)}` : 'Tarifa padrão'}
                  {plan.price && <span className="text-xs font-medium text-muted">/mês</span>}
                </p>
                {plan.discount_pct && (
                  <p className="mt-1 text-xs text-muted-2">{Number(plan.discount_pct)}% de desconto na tarifa vigente</p>
                )}
              </div>
            ))}
            {plans?.length === 0 && <p className="text-sm text-muted">Nenhum plano cadastrado ainda.</p>}
          </div>
        </div>

        <div>
          <h2 className="mb-3 font-heading text-[15px] font-bold text-ink">Usuários</h2>
          <div className="overflow-hidden rounded-[18px] border border-hairline bg-white shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
            <div className="grid grid-cols-[1.6fr_1.4fr_1fr_100px] bg-[#F4F2FB] px-[18px] py-3">
              <span className="text-[11px] font-bold text-muted">NOME</span>
              <span className="text-[11px] font-bold text-muted">E-MAIL</span>
              <span className="text-[11px] font-bold text-muted">CARTÃO RFID</span>
              <span className="text-[11px] font-bold text-muted">STATUS</span>
            </div>
            {users?.map((customer) => (
              <div
                key={customer.id}
                className="grid grid-cols-[1.6fr_1.4fr_1fr_100px] items-center border-b border-[#F4F2FB] px-[18px] py-3.5 last:border-b-0"
              >
                <span className="text-[13px] text-ink">{customer.full_name}</span>
                <span className="text-[13px] text-ink-soft">{customer.email}</span>
                <span className="text-[13px] text-ink-soft">{customer.rfid_virtual_id ?? '—'}</span>
                <button
                  type="button"
                  onClick={() => toggleBlockedMutation.mutate({ id: customer.id, blocked: !customer.blocked })}
                  className={`inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                    customer.blocked ? 'text-status-offline' : 'text-status-livre'
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${customer.blocked ? 'bg-status-offline' : 'bg-status-livre'}`}
                  />
                  {customer.blocked ? 'Bloqueado' : 'Ativo'}
                </button>
              </div>
            ))}
            {users?.length === 0 && <p className="px-[18px] py-4 text-sm text-muted">Nenhum cliente cadastrado ainda.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
