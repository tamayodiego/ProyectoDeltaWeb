import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import es from './locales/es.json'

export const LANGUAGES = ['es', 'en'] as const
export type Language = (typeof LANGUAGES)[number]

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { es: { translation: es }, en: { translation: en } },
    supportedLngs: LANGUAGES,
    load: 'languageOnly', // "es-MX" uses "es"
    fallbackLng: 'es',
    interpolation: { escapeValue: false }, // React already escapes
    detection: {
      // A choice made in the app wins over the browser's language
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'deltaweb-lang',
      caches: ['localStorage'],
    },
  })

// Screen readers and the browser's spell check read <html lang>
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18n
