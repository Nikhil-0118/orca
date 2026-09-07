import React, { createContext, useContext, useState, useEffect } from 'react';
import { LANGUAGES, DEFAULT_LANGUAGE } from './languages';
import { getTranslation } from './translations';

const LanguageContext = createContext(null);

const STORAGE_KEY = 'orca_user_language';
const HAS_SELECTED_KEY = 'orca_language_selected';

export function LanguageProvider({ children }) {
  const [currentLanguage, setCurrentLanguageState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && LANGUAGES.some(l => l.code === saved)) {
        return saved;
      }
    } catch {
      // Ignore storage errors
    }
    return DEFAULT_LANGUAGE;
  });

  const [isLanguageModalOpen, setIsLanguageModalOpen] = useState(() => {
    try {
      const hasChosen = localStorage.getItem(HAS_SELECTED_KEY);
      return !hasChosen; // Open modal on first visit if user hasn't chosen yet
    } catch {
      return false;
    }
  });

  const currentLangObj = LANGUAGES.find(l => l.code === currentLanguage) || LANGUAGES[1]; // default English or first

  const setLanguage = (code) => {
    const validLang = LANGUAGES.find(l => l.code === code);
    if (!validLang) return;
    
    setCurrentLanguageState(code);
    try {
      localStorage.setItem(STORAGE_KEY, code);
      localStorage.setItem(HAS_SELECTED_KEY, 'true');
    } catch (e) {
      console.warn('LocalStorage error setting language:', e);
    }

    // Set HTML lang and dir attributes
    if (typeof document !== 'undefined') {
      document.documentElement.lang = code;
      document.documentElement.dir = validLang.dir || 'ltr';
    }
  };

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = currentLanguage;
      document.documentElement.dir = currentLangObj?.dir || 'ltr';
    }
  }, [currentLanguage, currentLangObj]);

  const t = (key, fallback) => {
    const translated = getTranslation(currentLanguage, key);
    if (translated && translated !== key) return translated;
    return fallback || translated || key;
  };

  const openLanguageModal = () => setIsLanguageModalOpen(true);
  const closeLanguageModal = () => setIsLanguageModalOpen(false);

  return (
    <LanguageContext.Provider
      value={{
        currentLanguage,
        currentLangObj,
        languages: LANGUAGES,
        setLanguage,
        t,
        isLanguageModalOpen,
        openLanguageModal,
        closeLanguageModal,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return ctx;
}
