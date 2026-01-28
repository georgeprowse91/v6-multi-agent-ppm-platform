import React, { createContext, useContext, useMemo, useState } from 'react';
import en from './locales/en.json';
import pseudo from './locales/pseudo.json';

export type Locale = 'en' | 'pseudo';

type Messages = typeof en;

interface I18nContextValue {
  locale: Locale;
  t: (key: string) => string;
  setLocale: (locale: Locale) => void;
}

const messages: Record<Locale, Messages> = {
  en,
  pseudo,
};

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

function resolveMessage(bundle: Messages, key: string): string | undefined {
  const result = key.split('.').reduce<unknown>((current, part) => {
    if (!current || typeof current !== 'object') return undefined;
    return (current as Record<string, unknown>)[part];
  }, bundle as unknown);
  return typeof result === 'string' ? result : undefined;
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');

  const value = useMemo<I18nContextValue>(() => {
    const bundle = messages[locale] ?? messages.en;
    const t = (key: string) => resolveMessage(bundle, key) ?? key;
    return { locale, t, setLocale };
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
