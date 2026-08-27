import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AuthProvider, useAuth } from './lib/auth'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { FilaProprietarioPage } from './pages/FilaProprietarioPage'
import { FrotaPage } from './pages/FrotaPage'
import { LoginPage } from './pages/LoginPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { RelatoriosPage } from './pages/RelatoriosPage'
import { TarifasPage } from './pages/TarifasPage'
import { UsuariosPlanosPage } from './pages/UsuariosPlanosPage'
import { routes } from './routes'

const queryClient = new QueryClient()

const PAGE_COMPONENTS = {
  '/': DashboardPage,
  '/tarifas': TarifasPage,
  '/usuarios-planos': UsuariosPlanosPage,
  '/fila': FilaProprietarioPage,
  '/relatorios': RelatoriosPage,
  '/frota': FrotaPage,
  '/onboarding': OnboardingPage,
  '/assistente': ChatPage,
}

function RequireAuth({ children }) {
  const { token, loadingEstablishment } = useAuth()

  if (!token) return <Navigate to="/login" replace />
  if (loadingEstablishment) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Carregando…
      </div>
    )
  }
  return children
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              {routes.map((route) => {
                const Component = PAGE_COMPONENTS[route.path]
                return (
                  <Route
                    key={route.path}
                    path={route.path}
                    element={Component ? <Component /> : <PlaceholderPage title={route.title} />}
                  />
                )
              })}
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
