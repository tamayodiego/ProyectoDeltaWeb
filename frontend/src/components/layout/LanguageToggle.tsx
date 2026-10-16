import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

/** Shows the current language; a click switches to the other one. */
export function LanguageToggle() {
  const { t, i18n } = useTranslation()
  const current = i18n.resolvedLanguage === 'en' ? 'en' : 'es'

  return (
    <Button
      variant="ghost"
      size="lg"
      aria-label={t('header.switchLanguage')}
      onClick={() => void i18n.changeLanguage(current === 'es' ? 'en' : 'es')}
      className="font-mono text-xs font-semibold uppercase"
    >
      {current}
    </Button>
  )
}
