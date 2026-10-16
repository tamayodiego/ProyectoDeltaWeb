import { createContext } from 'react'

/** What the user picked. "system" follows the operating system's setting. */
export type Theme = 'light' | 'dark' | 'system'
/** What is on screen: 01 Laboratorio claro or 02 Pizarra oscura. */
export type ResolvedTheme = 'light' | 'dark'

// The same key is read by the inline script in index.html, before React starts
export const THEME_STORAGE_KEY = 'deltaweb-theme'
export const DARK_QUERY = '(prefers-color-scheme: dark)'

export function readStoredTheme(): Theme {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system' // storage can be blocked (private mode, strict settings)
  }
}

export function storeTheme(theme: Theme): void {
  try {
    if (theme === 'system') localStorage.removeItem(THEME_STORAGE_KEY)
    else localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Not saved: the choice still works until the page is reloaded
  }
}

export function resolveTheme(theme: Theme, systemPrefersDark: boolean): ResolvedTheme {
  if (theme === 'system') return systemPrefersDark ? 'dark' : 'light'
  return theme
}

/** The palettes live in index.css: :root is light, .dark is dark. */
export function applyTheme(resolved: ResolvedTheme): void {
  document.documentElement.classList.toggle('dark', resolved === 'dark')
}

export interface ThemeState {
  theme: Theme
  resolved: ResolvedTheme
  setTheme: (theme: Theme) => void
}

export const ThemeContext = createContext<ThemeState | null>(null)
