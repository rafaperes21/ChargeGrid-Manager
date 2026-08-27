import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FaqAccordion } from '../components/ui/FaqAccordion'
import { apiClient } from '../lib/apiClient'
import { useAuth } from '../lib/auth'
import { PUBLIC_FAQ, SUPPORT_CONTACT } from '../lib/faq'
import { formatCurrency, formatEnergyKwh } from '../lib/format'

// Tela de impacto (Prioridade 5, Tarefa 5.3) - antes do login, sem autenticacao
// (GET /fleet/impact e publico). Numeros reais da base de demonstracao atual, nunca
// inventados - se a base for pequena, aparece pequena mesmo.
function ImpactHero() {
  const { data } = useQuery({
    queryKey: ['fleet-impact'],
    queryFn: () => apiClient.get('/fleet/impact'),
  })

  if (!data) return null

  return (
    <div className="mb-6 w-full max-w-sm">
      <div className="grid grid-cols-3 gap-2 rounded-2xl border border-hairline bg-surface px-3 py-4 text-center">
        <div>
          <p className="font-heading text-lg font-bold text-ink">{formatEnergyKwh(data.total_kwh_managed)}</p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-2">gerenciados</p>
        </div>
        <div>
          <p className="font-heading text-lg font-bold text-ink">
            {Number(data.co2_avoided_kg).toFixed(1)} kg
          </p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-2">CO₂ evitado</p>
        </div>
        <div>
          <p className="font-heading text-lg font-bold text-ink">{formatCurrency(data.total_revenue_processed)}</p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-2">receita habilitada</p>
        </div>
      </div>
      <p className="mt-1.5 text-center text-[10px] text-muted-2">
        Dado real da base de demonstração atual ({data.establishments_count} estabelecimento
        {data.establishments_count !== 1 ? 's' : ''})
      </p>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('E-mail ou senha inválidos.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-cream p-4 font-body">
      <ImpactHero />
      <Card className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 24 24" className="shrink-0">
            <defs>
              <linearGradient id="loginBolt" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#FF7A1A" />
                <stop offset="55%" stopColor="#E60012" />
                <stop offset="100%" stopColor="#7C3AED" />
              </linearGradient>
            </defs>
            <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" fill="url(#loginBolt)" />
          </svg>
          <div>
            <h1 className="font-heading text-base font-bold text-ink">ChargeGrid-Manager</h1>
            <p className="text-xs text-muted-2">Portal do proprietário</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-muted-2">
            E-mail
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-xl border border-hairline px-3.5 py-2.5 text-sm text-ink focus:border-brand focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted-2">
            Senha
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-xl border border-hairline px-3.5 py-2.5 text-sm text-ink focus:border-brand focus:outline-none"
            />
          </label>
          {error && <p className="text-sm text-status-problema">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-2">
            {submitting ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>
      </Card>

      <div className="mt-8 w-full max-w-sm">
        <h2 className="mb-3 text-center text-xs font-bold uppercase tracking-wide text-muted">
          Perguntas frequentes
        </h2>
        <FaqAccordion items={PUBLIC_FAQ} />
        <p className="mt-4 text-center text-[11px] text-muted-2">
          Não achou o que procurava? {SUPPORT_CONTACT.email} · {SUPPORT_CONTACT.phone}
          <br />
          <span className="text-muted-3">({SUPPORT_CONTACT.note})</span>
        </p>
      </div>
    </div>
  )
}
