import { useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react'

import {
  applyTheme,
  DARK_QUERY,
  readStoredTheme,
  resolveTheme,
  storeTheme,
  ThemeContext,
  type Theme,
} from './theme'

// Keeps React in sync with the system setting, even if it changes while the app is open
function subscribe(onChange: () => void) {
  const query = window.matchMedia(DARK_QUERY)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}
const systemPrefersDark = () => window.matchMedia(DARK_QUERY).matches

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme)
  const prefersDark = useSyncExternalStore(subscribe, systemPrefersDark)
  const resolved = resolveTheme(theme, prefersDark)

  useEffect(() => {
    applyTheme(resolved)
  }, [resolved])

  const value = useMemo(
    () => ({
      theme,
      resolved,
      setTheme: (next: Theme) => {
        storeTheme(next)
        setThemeState(next)
      },
    }),
    [theme, resolved],
  )

  return <ThemeContext value={value}>{children}</ThemeContext>
}
