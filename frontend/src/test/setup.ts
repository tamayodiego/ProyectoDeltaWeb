// Adds DOM matchers to expect(): toBeInTheDocument(), toHaveTextContent()...
import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

import i18n from '@/i18n'

// jsdom has no matchMedia; pretend the system is in light mode
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
})

beforeEach(async () => {
  await i18n.changeLanguage('es') // jsdom's browser language is English
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.className = ''
})
