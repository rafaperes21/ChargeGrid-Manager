import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'chargegrid_theme'

function systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function resolveInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return systemPrefersDark() ? 'dark' : 'light'
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

// Chamado no main.jsx antes do primeiro render - evita piscar o tema errado por uma
// fracao de segundo enquanto o React ainda nao montou.
export function bootstrapTheme() {
  applyTheme(resolveInitialTheme())
}

export function useTheme() {
  const [theme, setThemeState] = useState(resolveInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  return { theme, toggleTheme }
}
