import { describe, expect, it } from 'vitest'

import { readStoredTheme, resolveTheme, storeTheme, THEME_STORAGE_KEY } from './theme'

describe('resolveTheme', () => {
  it('follows the system when the choice is "system"', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })

  it('an explicit choice wins over the system', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
  })
})

describe('stored theme', () => {
  it('is "system" when nothing was chosen', () => {
    expect(readStoredTheme()).toBe('system')
  })

  it('survives a reload', () => {
    storeTheme('dark')
    expect(readStoredTheme()).toBe('dark')
  })

  it('choosing "system" forgets the choice', () => {
    storeTheme('dark')
    storeTheme('system')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull()
  })

  it('ignores a garbage value', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'purple')
    expect(readStoredTheme()).toBe('system')
  })
})
