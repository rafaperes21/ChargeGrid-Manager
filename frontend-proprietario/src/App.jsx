import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AuthProvider, useAuth } from './lib/auth'
import { ChatPage } from './pages/ChatPage'
import { LoginPage } from './pages/LoginPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { routes } from './routes'

const queryClient = new QueryClient()

// So /assistente tem tela real por enquanto - o resto continua PlaceholderPage ate M4 sair.
const PAGE_COMPONENTS = {
  '/assistente': ChatPage,
}

function RequireAuth({ children }) {
  const { token, loadingEstablishment } = useAuth()

  if (!token) return <Navigate to="/login" replace />
  if (loadingEstablishment) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-400">
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
