import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { useAuth } from '../lib/auth'

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
    <div className="flex min-h-screen items-center justify-center bg-cream p-4 font-body">
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
            <p className="text-xs text-muted-2">Oi! Entre para carregar seu carro</p>
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
    </div>
  )
}
