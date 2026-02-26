import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { I18nProvider } from './i18n';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import { ThemeProvider } from './components/theme/ThemeProvider';
import 'shepherd.js/dist/css/shepherd.css';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <ThemeProvider>
        <ErrorBoundary showActions>
          <BrowserRouter basename={window.location.pathname.startsWith('/app') ? '/app' : '/'}>
            <App />
          </BrowserRouter>
        </ErrorBoundary>
      </ThemeProvider>
    </I18nProvider>
  </React.StrictMode>,
);
