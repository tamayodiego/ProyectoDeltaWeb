import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router'

export function DeltaMatroidPage() {
  const { t } = useTranslation()
  const { deltaMatroidId = '' } = useParams()
  return (
    <div>
      <h1 className="text-[34px] leading-tight font-bold tracking-tight">
        {t('pages.deltaMatroid', { id: deltaMatroidId })}
      </h1>
      <p className="mt-2 text-muted-foreground">{t('pages.placeholder', { block: '3c' })}</p>
    </div>
  )
}
