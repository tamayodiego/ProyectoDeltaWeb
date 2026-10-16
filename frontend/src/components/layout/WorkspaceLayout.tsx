import { FolderPlus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router'

import { Button } from '@/components/ui/button'

import { ApiStatus } from './ApiStatus'

/** The workspace: folder tree on the left, the selected delta-matroid on the right. */
export function WorkspaceLayout() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-1">
      <aside
        aria-label={t('workspace.title')}
        className="hidden w-[219px] shrink-0 flex-col border-r bg-sidebar min-[600px]:flex min-[1150px]:w-[252px]"
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h2 className="text-[10px] font-bold tracking-[1px] text-muted-foreground uppercase">
            {t('workspace.title')}
          </h2>
          <Button variant="ghost" size="icon-sm" aria-label={t('workspace.newFolder')}>
            <FolderPlus aria-hidden="true" />
          </Button>
        </div>
        <p className="flex-1 px-5 text-xs text-muted-foreground">{t('workspace.treeSoon')}</p>
        <ApiStatus />
      </aside>
      <main className="min-w-0 flex-1 px-10 pt-7 pb-6">
        <div className="mx-auto max-w-[1400px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
