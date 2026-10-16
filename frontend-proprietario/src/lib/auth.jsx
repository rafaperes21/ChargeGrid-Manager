import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { WrongPortalError, apiClient, getToken, setToken as persistToken } from './apiClient'

// Auth minima: login por e-mail/senha contra o backend, token em localStorage. Sem registro,
// "esqueci a senha" ou Google Sign-In — fora do escopo desta rodada.
const AuthContext = createContext(null)

// Cada portal so aceita o seu perfil. Sem isso, um token salvo pelo outro portal (o navegador
// guarda o login por porta, e as portas ja trocaram entre execucoes do dev.sh) entrava direto
// e o assistente respondia 403 com uma mensagem generica de "tente de novo".
const PORTAL_ROLE = 'owner'
const WRONG_PORTAL_MESSAGE = 'Esta conta é de cliente — entre pelo portal do cliente.'

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken())
  const [user, setUser] = useState(null)
  const [establishment, setEstablishment] = useState(null)
  const [loadingEstablishment, setLoadingEstablishment] = useState(Boolean(getToken()))
  const [notice, setNotice] = useState(null)

  const logout = useCallback(() => {
    persistToken(null)
    setTokenState(null)
    setUser(null)
    setEstablishment(null)
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token: accessToken } = await apiClient.post('/auth/login', { email, password })
    persistToken(accessToken)
    const me = await apiClient.get('/users/me')
    if (me.role !== PORTAL_ROLE) {
      persistToken(null)
      throw new WrongPortalError(WRONG_PORTAL_MESSAGE)
    }
    setNotice(null)
    setTokenState(accessToken)
    const establishments = await apiClient.get('/establishments/me')
    setUser(me)
    setEstablishment(establishments[0] ?? null)
  }, [])

  // Restaura usuario/estabelecimento apos um reload de pagina com token ja salvo.
  useEffect(() => {
    if (!token || user) {
      setLoadingEstablishment(false)
      return
    }
    let cancelled = false
    apiClient
      .get('/users/me')
      .then(async (me) => {
        if (me.role !== PORTAL_ROLE) {
          if (!cancelled) {
            setNotice(WRONG_PORTAL_MESSAGE)
            logout()
          }
          return
        }
        const establishments = await apiClient.get('/establishments/me')
        if (!cancelled) {
          setUser(me)
          setEstablishment(establishments[0] ?? null)
        }
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
    <AuthContext.Provider value={{ token, user, establishment, loadingEstablishment, login, logout, notice }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return context
}
