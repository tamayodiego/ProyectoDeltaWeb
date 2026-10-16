import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { THEME_STORAGE_KEY } from '@/theme/theme'
import { ThemeProvider } from '@/theme/ThemeProvider'

import { LanguageToggle } from './LanguageToggle'
import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  it('switches to dark and back, and remembers the choice', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    const html = document.documentElement
    expect(html).not.toHaveClass('dark')

    await user.click(screen.getByRole('button', { name: 'Cambiar a modo oscuro' }))
    expect(html).toHaveClass('dark')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')

    await user.click(screen.getByRole('button', { name: 'Cambiar a modo claro' }))
    expect(html).not.toHaveClass('dark')
  })
})

describe('LanguageToggle', () => {
  it('switches the interface and <html lang> to English', async () => {
    const user = userEvent.setup()
    render(<LanguageToggle />)

    await user.click(screen.getByRole('button', { name: 'Cambiar idioma a inglés' }))

    expect(screen.getByRole('button', { name: 'Switch language to Spanish' })).toHaveTextContent(
      'en',
    )
    expect(document.documentElement.lang).toBe('en')
  })
})
