import { Outlet } from 'react-router'

import { LanguageToggle } from './LanguageToggle'
import { Logo } from './Logo'
import { ThemeToggle } from './ThemeToggle'

/** Login, register...: no navigation, the form centered. */
export function AuthLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex items-center gap-2 px-6 py-4">
        <Logo />
        <div className="flex-1" />
        <LanguageToggle />
        <ThemeToggle />
      </header>
      <main className="flex flex-1 justify-center px-4 pt-8 pb-16">
        <div className="w-full max-w-[400px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
