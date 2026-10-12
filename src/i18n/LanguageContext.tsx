import React, { createContext, useContext, useState, useEffect } from "react"
import { TRANSLATIONS, SupportedLanguage } from "./translations"

interface LanguageContextType {
  language: SupportedLanguage
  setLanguage: (lang: SupportedLanguage) => void
  t: (key: string, defaultText?: string) => string
}

const LanguageContext = createContext<LanguageContextType>({
  language: "pt",
  setLanguage: () => {},
  t: (key: string, defaultText?: string) => defaultText || key
})

const STORAGE_KEY = "laptop_hunter_language"

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === "en" || saved === "pt") {
      return saved
    }
    return "pt"
  })

  // Sync with /api/settings if available
  useEffect(() => {
    const fetchSavedLanguage = async () => {
      try {
        const res = await fetch("/api/settings")
        if (res.ok) {
          const data = await res.json()
          if (data.language && (data.language === "en" || data.language === "pt")) {
            setLanguageState(data.language)
            localStorage.setItem(STORAGE_KEY, data.language)
          }
        }
      } catch {
        // Fallback to local storage
      }
    }
    fetchSavedLanguage()
  }, [])

  const setLanguage = (newLang: SupportedLanguage) => {
    setLanguageState(newLang)
    localStorage.setItem(STORAGE_KEY, newLang)
  }

  const t = (key: string, defaultText?: string): string => {
    const table = TRANSLATIONS[language] || TRANSLATIONS.pt
    if (table && table[key]) {
      return table[key]
    }
    const fallbackTable = TRANSLATIONS.pt
    if (fallbackTable && fallbackTable[key]) {
      return fallbackTable[key]
    }
    return defaultText || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
