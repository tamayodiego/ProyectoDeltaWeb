import { useTranslation } from 'react-i18next'
import { Link, NavLink } from 'react-router'

import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { LanguageToggle } from './LanguageToggle'
import { Logo } from './Logo'
import { ThemeToggle } from './ThemeToggle'

const NAV = [
  { to: '/workspace', label: 'nav.workspace' },
  { to: '/new', label: 'nav.new' },
  { to: '/isomorphism', label: 'nav.isomorphism' },
] as const

export function AppHeader() {
  const { t } = useTranslation()

  return (
    <header className="flex h-[73px] shrink-0 items-center gap-7 border-b bg-card px-6">
      <Logo />
      <nav aria-label={t('nav.main')} className="hidden gap-6 self-stretch min-[600px]:flex">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                '-mb-px flex items-center border-b-2 transition-colors',
                isActive
                  ? 'border-primary font-semibold text-primary'
                  : 'border-transparent font-medium text-muted-foreground hover:text-foreground',
              )
            }
          >
            {t(item.label)}
          </NavLink>
        ))}
      </nav>
      <div className="flex-1" />
      <div className="flex items-center gap-2">
        <LanguageToggle />
        <ThemeToggle />
        {/* Becomes the account menu once we know who is logged in (block 3b) */}
        <Link to="/login" className={buttonVariants({ size: 'lg' })}>
          {t('header.login')}
        </Link>
      </div>
    </header>
  )
}
