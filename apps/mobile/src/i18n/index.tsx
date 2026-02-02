import React, { createContext, useContext, useMemo, useState } from 'react';
import en from './locales/en.json';
import de from './locales/de.json';

export type Locale = 'en' | 'de';

type Messages = Record<string, string>;

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
}

const messages: Record<Locale, Messages> = {
  en,
  de,
};

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

function formatMessage(template: string, values?: Record<string, string | number>) {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? `{${key}}`));
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');

  const value = useMemo<I18nContextValue>(() => {
    const bundle = messages[locale] ?? messages.en;
    const t = (key: string, values?: Record<string, string | number>) => {
      const message = bundle[key] ?? key;
      return formatMessage(message, values);
    };
    return { locale, setLocale, t };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider');
  }
  return context;
}
