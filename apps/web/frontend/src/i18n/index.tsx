import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { IntlProvider, useIntl } from 'react-intl';
import en from './locales/en.json';
import de from './locales/de.json';

export type Locale = 'en' | 'de';

type Messages = Record<string, string>;

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const STORAGE_KEY = 'ppm-locale';

const messages: Record<Locale, Messages> = {
  en,
  de,
};

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'de') {
      setLocale(stored);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nContextValue>(() => ({ locale, setLocale }), [locale]);

  return (
    <I18nContext.Provider value={value}>
      <IntlProvider locale={locale} messages={messages[locale]} defaultLocale="en">
        {children}
      </IntlProvider>
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  const intl = useIntl();
  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider');
  }
  const t = (id: string, values?: Record<string, string | number>) =>
    intl.formatMessage({ id, defaultMessage: id }, values);
  return { ...context, t };
}
