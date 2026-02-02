import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '@/store';
import { useTour } from '@/components/tours';
import { Icon } from '@/components/icon/Icon';
import { useTranslation } from '@/i18n';
import { useTheme } from '@/components/theme/ThemeProvider';
import styles from './Header.module.css';

interface BreadcrumbItem {
  label: string;
  path?: string;
}

function getBreadcrumbs(pathname: string, t: (key: string) => string): BreadcrumbItem[] {
  const parts = pathname.split('/').filter(Boolean);
  const crumbs: BreadcrumbItem[] = [{ label: t('header.home'), path: '/' }];

  if (parts.length === 0) {
    return crumbs;
  }

  if (parts[0] === 'portfolio' && parts[1]) {
    crumbs.push({ label: t('header.portfolio'), path: `/portfolio/${parts[1]}` });
  } else if (parts[0] === 'program' && parts[1]) {
    crumbs.push({ label: t('header.program'), path: `/program/${parts[1]}` });
  } else if (parts[0] === 'project' && parts[1]) {
    crumbs.push({ label: t('header.project'), path: `/project/${parts[1]}` });
  } else if (parts[0] === 'config') {
    crumbs.push({ label: t('header.configuration') });
    if (parts[1] === 'agents') {
      crumbs.push({ label: t('header.agents'), path: '/config/agents' });
    } else if (parts[1] === 'connectors') {
      crumbs.push({ label: t('header.connectors'), path: '/config/connectors' });
    } else if (parts[1] === 'workflows') {
      crumbs.push({ label: t('header.workflows'), path: '/config/workflows' });
    }
  }

  return crumbs;
}

export function Header() {
  const location = useLocation();
  const { session } = useAppStore();
  const { startTour } = useTour();
  const { t, locale, setLocale } = useTranslation();
  const { mode, setMode } = useTheme();
  const breadcrumbs = getBreadcrumbs(location.pathname, t);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const menuId = 'user-settings-menu';

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        !buttonRef.current?.contains(event.target as Node)
      ) {
        setMenuOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [menuOpen]);

  const toggleMenu = () => setMenuOpen((prev) => !prev);

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link to="/" className={styles.logo}>
          <Icon semantic="domain.platform" decorative size="lg" color="accent" />
          <span className={styles.logoText}>PPM Platform</span>
        </Link>

        <nav className={styles.breadcrumb} aria-label="Breadcrumb">
          <ol>
            {breadcrumbs.map((crumb, index) => (
              <li key={crumb.path ?? index}>
                {index > 0 && (
                  <span className={styles.separator} aria-hidden="true">
                    /
                  </span>
                )}
                {crumb.path && index < breadcrumbs.length - 1 ? (
                  <Link to={crumb.path}>{crumb.label}</Link>
                ) : (
                  <span aria-current={index === breadcrumbs.length - 1 ? 'page' : undefined}>
                    {crumb.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>

      <div className={styles.right}>
        <button
          className={styles.helpButton}
          type="button"
          title={t('header.helpTitle')}
          onClick={startTour}
          data-tour="help-menu"
        >
          <span>{t('header.help')}</span>
          <Icon semantic="actions.help" decorative />
        </button>
        <div className={styles.languageSelector}>
          <label className={styles.visuallyHidden} htmlFor="language-select">
            {t('header.language')}
          </label>
          <select
            id="language-select"
            className={styles.languageSelect}
            value={locale}
            onChange={(event) => setLocale(event.target.value as typeof locale)}
          >
            <option value="en">English</option>
            <option value="de">Deutsch</option>
          </select>
        </div>
        <button
          className={styles.iconButton}
          type="button"
          title={t('header.notifications')}
          aria-label={t('header.notifications')}
        >
          <Icon semantic="communication.notifications" label={t('header.notifications')} />
        </button>

        <button
          className={styles.iconButton}
          type="button"
          title={t('header.settings')}
          aria-label={t('header.settings')}
        >
          <Icon semantic="actions.settings" label={t('header.settings')} />
        </button>

        <div className={styles.userMenu}>
          <button
            className={styles.userButton}
            type="button"
            onClick={toggleMenu}
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            aria-controls={menuOpen ? menuId : undefined}
            ref={buttonRef}
          >
            <div className={styles.avatar}>
              {session.user?.name?.charAt(0).toUpperCase() ?? 'U'}
            </div>
            <span className={styles.userName}>
              {session.user?.name ?? t('header.userLabel')}
            </span>
          </button>
          {menuOpen && (
            <div
              className={styles.userMenuPanel}
              id={menuId}
              role="dialog"
              aria-modal="false"
              aria-label={t('header.userMenu')}
              ref={menuRef}
            >
              <div className={styles.menuSection} role="none">
                <label className={styles.menuLabel} htmlFor="theme-select">
                  {t('header.theme')}
                </label>
                <select
                  id="theme-select"
                  className={styles.menuSelect}
                  value={mode}
                  onChange={(event) => setMode(event.target.value as typeof mode)}
                >
                  <option value="light">{t('header.themeLight')}</option>
                  <option value="dark">{t('header.themeDark')}</option>
                  <option value="high-contrast">{t('header.themeHighContrast')}</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
