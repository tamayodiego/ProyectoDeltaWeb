import { useContext } from 'react'

import { ThemeContext, type ThemeState } from './theme'

export function useTheme(): ThemeState {
  const state = useContext(ThemeContext)
  if (state === null) throw new Error('useTheme must be used inside <ThemeProvider>')
  return state
}
