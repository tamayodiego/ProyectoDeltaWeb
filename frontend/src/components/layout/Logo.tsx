import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

export function Logo() {
  const { t } = useTranslation()
  return (
    <Link to="/workspace" className="flex items-center gap-2.5 text-foreground no-underline">
      <span
        aria-hidden="true"
        className="flex size-8 items-center justify-center rounded-md bg-primary text-lg font-bold text-primary-foreground"
      >
        Δ
      </span>
      <span className="text-[19px] font-bold tracking-tight">{t('app.name')}</span>
    </Link>
  )
}
