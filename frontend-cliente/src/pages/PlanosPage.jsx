import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { apiClient } from '../lib/apiClient'
import { formatCurrency, formatEnergyKwh } from '../lib/format'

// Catalogo fixo da plataforma (skill tarifacao-e-sessoes secao 4) - o estabelecimento so
// escolhe quais niveis habilita (`GET /establishments/{id}/plans`, so os habilitados), nunca
// o valor. Assinar so grava a escolha (`POST /subscriptions`); nao ha cobranca de mensalidade
// de verdade, mesmo espirito declarativo do resto do sistema.
export function PlanosPage() {
  const { establishmentId } = useParams()
  const queryClient = useQueryClient()

  const { data: establishments } = useQuery({
    queryKey: ['establishments'],
    queryFn: () => apiClient.get('/establishments'),
  })
  const establishment = establishments?.find((item) => item.id === establishmentId)

  const { data: plans, isLoading } = useQuery({
    queryKey: ['plans', establishmentId],
    queryFn: () => apiClient.get(`/establishments/${establishmentId}/plans`),
    enabled: Boolean(establishmentId),
  })

  const { data: subscription } = useQuery({
    queryKey: ['subscription', establishmentId],
    queryFn: () => apiClient.get(`/subscriptions/me?establishment_id=${establishmentId}`),
    enabled: Boolean(establishmentId),
  })

  const subscribeMutation = useMutation({
    mutationFn: (planId) => apiClient.post('/subscriptions', { plan_id: planId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscription', establishmentId] }),
  })

  // Sem assinatura ativa == avulso (mesmo criterio do backend, services/sessions.py) - nunca
  // um estado "sem plano" a parte.
  const activeKind = subscription?.plan?.kind ?? 'avulso'
  const avulsoPlan = plans?.find((plan) => plan.kind === 'avulso')

  return (
    <div className="flex flex-1 flex-col">
      <div className="bg-ink-fixed px-5 pb-4 pt-[18px] text-white">
        <Link to={`/mapa/${establishmentId}`} className="text-xs text-white/70">
          ← {establishment?.name ?? 'Estabelecimento'}
        </Link>
        <p className="mt-1 text-[15px] font-semibold">Planos</p>
      </div>

      <div className="flex flex-col gap-3 p-5">
        <p className="text-xs text-muted-2">
          Catálogo fixo definido pela plataforma — o estabelecimento só escolhe quais níveis
          oferece, o preço e o desconto nunca mudam por conta dele.
        </p>

        {isLoading && (
          <>
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </>
        )}

        {plans?.map((plan) => {
          const isActive = plan.kind === activeKind
          return (
            <Card key={plan.id}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-ink">{plan.name}</p>
                {isActive && (
                  <span className="rounded-full bg-status-livre/10 px-2.5 py-1 text-[11px] font-semibold text-status-livre">
                    Plano atual
                  </span>
                )}
              </div>
              <p className="mt-1 text-2xl font-bold text-ink">
                {plan.price != null ? `${formatCurrency(plan.price)}/mês` : 'Sem mensalidade'}
              </p>
              <div className="mt-2 flex flex-col gap-1 text-xs text-muted-2">
                {plan.free_kwh_allowance != null && (
                  <span>{formatEnergyKwh(plan.free_kwh_allowance)} inclusos por ciclo</span>
                )}
                {Number(plan.discount_pct) > 0 && (
                  <span>{Number(plan.discount_pct)}% de desconto na tarifa</span>
                )}
                {plan.kind === 'avulso' && <span>Paga só pelo que carregar, sem compromisso</span>}
              </div>
              {!isActive && (
                <Button
                  className="mt-3 w-full"
                  variant="secondary"
                  disabled={subscribeMutation.isPending}
                  onClick={() => subscribeMutation.mutate(plan.id)}
                >
                  Assinar
                </Button>
              )}
              {isActive && plan.kind !== 'avulso' && (
                <Button
                  className="mt-3 w-full"
                  variant="secondary"
                  disabled={subscribeMutation.isPending || !avulsoPlan}
                  onClick={() => subscribeMutation.mutate(avulsoPlan.id)}
                >
                  Cancelar assinatura
                </Button>
              )}
            </Card>
          )
        })}

        {plans?.length === 1 && (
          <p className="text-xs text-muted-3">
            Este estabelecimento ainda não habilitou planos com desconto — só o avulso está
            disponível.
          </p>
        )}
      </div>
    </div>
  )
}
