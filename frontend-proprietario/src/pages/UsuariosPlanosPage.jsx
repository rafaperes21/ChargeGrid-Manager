import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'

const PLAN_KIND_LABELS = { avulso: 'Avulso', mensal: 'Mensal', trimestral: 'Trimestral' }

function PlanToggle({ plan, onToggle, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={plan.enabled}
      aria-label={`${plan.enabled ? 'Desativar' : 'Ativar'} plano ${PLAN_KIND_LABELS[plan.kind]}`}
      disabled={disabled}
      onClick={() => onToggle(plan)}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
        plan.enabled ? 'bg-brand' : 'bg-hairline'
      }`}
    >
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface shadow transition-transform ${
          plan.enabled ? 'translate-x-[18px]' : 'translate-x-0.5'
        }`}
      />
    </button>
  )
}

export function UsuariosPlanosPage() {
  const { establishment } = useAuth()
  const queryClient = useQueryClient()

  const { data: plans } = useQuery({
    queryKey: ['plans', establishment?.id],
    queryFn: () => apiClient.get(`/plans?establishment_id=${establishment.id}`),
    enabled: Boolean(establishment),
  })

  const { data: users } = useQuery({
    queryKey: ['customers'],
    queryFn: () => apiClient.get('/users'),
  })

  const togglePlanMutation = useMutation({
    mutationFn: ({ id, enabled }) => apiClient.patch(`/plans/${id}`, { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plans', establishment?.id] }),
  })

  const toggleBlockedMutation = useMutation({
    mutationFn: ({ id, blocked }) => apiClient.patch(`/users/${id}`, { blocked }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers'] }),
  })

  if (!establishment) return null

  const sortedPlans = plans ? [...plans].sort((a, b) => a.priority - b.priority) : []

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-8 pt-7">
        <h1 className="font-heading text-[21px] font-bold text-ink">Usuários e planos</h1>
        <p className="mt-1 text-[13px] text-muted-2">Cartões RFID cadastrados e planos de assinatura</p>
      </div>

      <div className="flex flex-col gap-6 p-8">
        <div>
          <h2 className="mb-1 font-heading text-[15px] font-bold text-ink">Planos</h2>
          <p className="mb-3 text-xs text-muted-2">
            Catálogo definido pela plataforma — escolha quais níveis este estabelecimento oferece.
            Valores e regras não são editáveis por aqui.
          </p>
          <div className="grid grid-cols-3 gap-4">
            {sortedPlans.map((plan) => (
              <div
                key={plan.id}
                className={`rounded-[18px] border p-5 shadow-[0_2px_14px_rgba(14,10,26,0.05)] transition-opacity ${
                  plan.enabled ? 'border-brand bg-surface' : 'border-hairline bg-surface opacity-60'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-bold uppercase tracking-wide text-muted">
                    {PLAN_KIND_LABELS[plan.kind]}
                  </p>
                  <PlanToggle
                    plan={plan}
                    disabled={togglePlanMutation.isPending}
                    onToggle={(p) => togglePlanMutation.mutate({ id: p.id, enabled: !p.enabled })}
                  />
                </div>
                <p className="mt-2 text-2xl font-bold text-ink">
                  {plan.price ? `R$ ${Number(plan.price).toFixed(2)}` : 'Tarifa padrão'}
                  {plan.price && <span className="text-xs font-medium text-muted">/mês</span>}
                </p>
                {Number(plan.discount_pct) > 0 && (
                  <p className="mt-1 text-xs text-muted-2">{Number(plan.discount_pct)}% de desconto na tarifa vigente</p>
                )}
                {plan.free_kwh_allowance && (
                  <p className="mt-1 text-xs text-muted-2">{Number(plan.free_kwh_allowance)} kWh de franquia mensal</p>
                )}
              </div>
            ))}
            {sortedPlans.length === 0 && <p className="text-sm text-muted">Nenhum plano cadastrado ainda.</p>}
          </div>
        </div>

        <div>
          <h2 className="mb-3 font-heading text-[15px] font-bold text-ink">Usuários</h2>
          <div className="overflow-hidden rounded-[18px] border border-hairline bg-surface shadow-[0_2px_14px_rgba(14,10,26,0.05)]">
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
