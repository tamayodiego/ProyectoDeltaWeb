import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

export function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      <h1 className="text-[34px] leading-tight font-bold tracking-tight">{t('pages.notFound')}</h1>
      <Link to="/workspace" className="mt-2 inline-block text-primary">
        {t('pages.backToWorkspace')}
      </Link>
    </div>
  )
}
