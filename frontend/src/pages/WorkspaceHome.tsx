import { useTranslation } from 'react-i18next'

export function WorkspaceHome() {
  const { t } = useTranslation()
  return <p className="text-muted-foreground">{t('workspace.select')}</p>
}
