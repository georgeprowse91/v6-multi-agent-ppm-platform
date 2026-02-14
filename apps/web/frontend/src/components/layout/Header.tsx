import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store';
import { useTour } from '@/components/tours';
import { Icon } from '@/components/icon/Icon';
import { FocusTrap } from '@/components/ui/FocusTrap';
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
  const navigate = useNavigate();
  const { session, featureFlags } = useAppStore();
  const { startTour } = useTour();
  const { t, locale, setLocale } = useTranslation();
  const { mode, setMode } = useTheme();
  const breadcrumbs = getBreadcrumbs(location.pathname, t);
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const menuRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const menuId = 'user-settings-menu';
  const notificationsEnabled = featureFlags.agent_async_notifications === true;

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (location.pathname === '/search') {
      setSearchQuery(params.get('q') ?? '');
    }
  }, [location.pathname, location.search]);

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
    document.addEventListener('mousedown', handleClick);
    return () => {
      document.removeEventListener('mousedown', handleClick);
    };
  }, [menuOpen]);

  const toggleMenu = () => setMenuOpen((prev) => !prev);
  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!searchQuery.trim()) {
      return;
    }
    navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
  };

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

      <form className={styles.searchForm} onSubmit={handleSearchSubmit}>
        <label className={styles.visuallyHidden} htmlFor="global-header-search">
          Global search
        </label>
        <input
          id="global-header-search"
          className={styles.searchInput}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search across portfolios"
          aria-label="Global search"
        />
        <button className={styles.searchButton} type="submit">
          Search
        </button>
      </form>

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
        {notificationsEnabled ? (
          <Link
            className={styles.iconButton}
            to="/notifications"
            title={t('header.notifications')}
            aria-label={t('header.notifications')}
          >
            <Icon semantic="communication.notifications" label={t('header.notifications')} />
          </Link>
        ) : (
          <button
            className={styles.iconButton}
            type="button"
            title={t('header.notifications')}
            aria-label={t('header.notifications')}
          >
            <Icon semantic="communication.notifications" label={t('header.notifications')} />
          </button>
        )}

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
            <FocusTrap
              className={styles.userMenuPanel}
              id={menuId}
              role="dialog"
              aria-modal="true"
              aria-label={t('header.userMenu')}
              ref={menuRef}
              onClose={() => setMenuOpen(false)}
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
            </FocusTrap>
          )}
        </div>
      </div>
    </header>
  );
}
