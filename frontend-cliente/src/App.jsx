import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AuthProvider, useAuth } from './lib/auth'
import { AjudaPage } from './pages/AjudaPage'
import { FilaPage } from './pages/FilaPage'
import { HistoricoPage } from './pages/HistoricoPage'
import { LoginPage } from './pages/LoginPage'
import { MapaDetalhePage } from './pages/MapaDetalhePage'
import { MapaPage } from './pages/MapaPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { SessaoPage } from './pages/SessaoPage'
import { routes } from './routes'

const queryClient = new QueryClient()

const PAGE_COMPONENTS = {
  '/': SessaoPage,
  '/mapa': MapaPage,
  '/historico': HistoricoPage,
  '/fila': FilaPage,
  '/ajuda': AjudaPage,
}

function RequireAuth({ children }) {
  const { token, loadingUser } = useAuth()

  if (!token) return <Navigate to="/login" replace />
  if (loadingUser) {
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
              <Route path="/mapa/:establishmentId" element={<MapaDetalhePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
