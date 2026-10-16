import { useTranslation } from 'react-i18next'

type TitleKey =
  | 'nav.new'
  | 'nav.isomorphism'
  | 'auth.login'
  | 'auth.register'
  | 'auth.forgot'
  | 'auth.reset'
  | 'auth.verify'

/** Stand-in for screens of later blocks, so every route already exists. */
export function PlaceholderPage({ titleKey, block }: { titleKey: TitleKey; block: string }) {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      <h1 className="text-[34px] leading-tight font-bold tracking-tight">{t(titleKey)}</h1>
      <p className="mt-2 text-muted-foreground">{t('pages.placeholder', { block })}</p>
    </div>
  )
}
