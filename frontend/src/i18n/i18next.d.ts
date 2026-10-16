import 'i18next'

import type es from './locales/es.json'

// t('nav.workspace') is type-checked: a missing or misspelled key is a compile error.
// Spanish is the reference; en.json must have the same keys.
declare module 'i18next' {
  interface CustomTypeOptions {
    resources: { translation: typeof es }
  }
}
