import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import enDivination from './locales/en/divination.json';
import enUi from './locales/en/ui.json';
import zhtwDivination from './locales/zhtw/divination.json';
import zhtwUi from './locales/zhtw/ui.json';

const dictionaries = {
  en: {
    ui: enUi,
    divination: enDivination,
  },
  zhtw: {
    ui: zhtwUi,
    divination: zhtwDivination,
  },
} as const;

export type LocaleCode = keyof typeof dictionaries;
export const LOCALE_CODES: LocaleCode[] = ['en', 'zhtw'];

type LocaleMessages = (typeof dictionaries)[LocaleCode];

interface I18nContextValue {
  locale: LocaleCode;
  setLocale: (locale: LocaleCode) => void;
  messages: LocaleMessages;
}

const STORAGE_KEY = 'app_locale';

const I18nContext = createContext<I18nContextValue | null>(null);

const isLocaleCode = (value: string): value is LocaleCode => LOCALE_CODES.includes(value as LocaleCode);

const resolveInitialLocale = (): LocaleCode => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && isLocaleCode(stored)) {
    return stored;
  }
  return 'en';
};

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocale] = useState<LocaleCode>(resolveInitialLocale);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, locale);
  }, [locale]);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      messages: dictionaries[locale],
    }),
    [locale]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = (): I18nContextValue => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
};
