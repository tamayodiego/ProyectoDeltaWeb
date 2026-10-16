import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useTheme } from '@/theme/useTheme'

/** Light (01 Laboratorio claro) <-> dark (02 Pizarra oscura). */
export function ThemeToggle() {
  const { t } = useTranslation()
  const { resolved, setTheme } = useTheme()
  const toDark = resolved === 'light'

  return (
    <Button
      variant="outline"
      size="icon-lg"
      aria-label={t(toDark ? 'header.toDark' : 'header.toLight')}
      onClick={() => setTheme(toDark ? 'dark' : 'light')}
    >
      {toDark ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
    </Button>
  )
}
