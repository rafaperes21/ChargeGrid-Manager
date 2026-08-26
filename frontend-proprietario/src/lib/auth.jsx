import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { apiClient, getToken, setToken as persistToken } from './apiClient'

// Auth minima: login por e-mail/senha contra o backend, token em localStorage. Sem registro,
// "esqueci a senha" ou Google Sign-In — fora do escopo desta rodada.
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken())
  const [establishment, setEstablishment] = useState(null)
  const [loadingEstablishment, setLoadingEstablishment] = useState(Boolean(getToken()))

  const logout = useCallback(() => {
    persistToken(null)
    setTokenState(null)
    setEstablishment(null)
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token: accessToken } = await apiClient.post('/auth/login', { email, password })
    persistToken(accessToken)
    setTokenState(accessToken)

    const establishments = await apiClient.get('/establishments/me')
    setEstablishment(establishments[0] ?? null)
  }, [])

  // Restaura o estabelecimento apos um reload de pagina com token ja salvo.
  useEffect(() => {
    if (!token || establishment) {
      setLoadingEstablishment(false)
      return
    }
    let cancelled = false
    apiClient
      .get('/establishments/me')
      .then((establishments) => {
        if (!cancelled) setEstablishment(establishments[0] ?? null)
      })
      .catch(() => {
        if (!cancelled) logout()
      })
      .finally(() => {
        if (!cancelled) setLoadingEstablishment(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return (
    <AuthContext.Provider value={{ token, establishment, loadingEstablishment, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return context
}
