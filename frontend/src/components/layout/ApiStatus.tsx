import { useTranslation } from 'react-i18next'

import { useApiStatus } from '@/api/useApiStatus'
import { cn } from '@/lib/utils'

/** Sidebar footer: a status dot and the backend version (also proves the proxy works). */
export function ApiStatus() {
  const { t } = useTranslation()
  const { data, isError } = useApiStatus()

  return (
    <div className="flex items-center gap-2 border-t px-5 py-3.5 text-[11px] text-muted-foreground">
      <span
        aria-hidden="true"
        className={cn('size-[5px] rounded-full', isError ? 'bg-destructive' : 'bg-primary')}
      />
      <span role="status">
        {isError ? t('workspace.apiDown') : data && t('workspace.apiOk', { version: data.version })}
      </span>
    </div>
  )
}
