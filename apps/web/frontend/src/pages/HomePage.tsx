import { Link } from 'react-router-dom';
import { useCanvasStore, SAMPLE_ARTIFACT_IDS } from '@/store/useCanvasStore';
import { Icon } from '@/components/icon/Icon';
import { OnboardingTour } from '@/components/onboarding/OnboardingTour';
import { useTranslation } from '@/i18n';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './HomePage.module.css';

export function HomePage() {
  const { artifacts, openArtifact } = useCanvasStore();
  const { t } = useTranslation();

  const quickLinks: { title: string; description: string; path: string; icon: IconSemantic }[] =
    [
      {
        title: t('home.quickLinks.portfolios.title'),
        description: t('home.quickLinks.portfolios.description'),
        path: '/portfolio/demo',
        icon: 'domain.portfolio',
      },
      {
        title: t('home.quickLinks.programs.title'),
        description: t('home.quickLinks.programs.description'),
        path: '/program/demo',
        icon: 'domain.program',
      },
      {
        title: t('home.quickLinks.projects.title'),
        description: t('home.quickLinks.projects.description'),
        path: '/project/demo',
        icon: 'domain.project',
      },
    ];

  const configLinks = [
    {
      title: t('home.config.agents.title'),
      description: t('home.config.agents.description'),
      path: '/config/agents',
    },
    {
      title: t('home.config.connectors.title'),
      description: t('home.config.connectors.description'),
      path: '/config/connectors',
    },
    {
      title: t('home.config.marketplace.title'),
      description: t('home.config.marketplace.description'),
      path: '/marketplace/connectors',
    },
    {
      title: t('home.config.workflows.title'),
      description: t('home.config.workflows.description'),
      path: '/config/workflows',
    },
  ];

  const handleOpenCharter = () => {
    const artifact = artifacts[SAMPLE_ARTIFACT_IDS.charter];
    if (artifact) openArtifact(artifact);
  };

  const handleOpenWBS = () => {
    const artifact = artifacts[SAMPLE_ARTIFACT_IDS.wbs];
    if (artifact) openArtifact(artifact);
  };

  const handleOpenTimeline = () => {
    const artifact = artifacts[SAMPLE_ARTIFACT_IDS.timeline];
    if (artifact) openArtifact(artifact);
  };

  const handleOpenSpreadsheet = () => {
    const artifact = artifacts[SAMPLE_ARTIFACT_IDS.spreadsheet];
    if (artifact) openArtifact(artifact);
  };

  const handleOpenDashboard = () => {
    const artifact = artifacts[SAMPLE_ARTIFACT_IDS.dashboard];
    if (artifact) openArtifact(artifact);
  };

  return (
    <div className={styles.page}>
      <OnboardingTour />
      <header className={styles.header} data-tour="home-header">
        <h1 className={styles.title}>{t('home.title')}</h1>
        <p className={styles.subtitle}>{t('home.subtitle')}</p>
      </header>

      <section className={styles.section} data-tour="home-canvas">
        <h2 className={styles.sectionTitle}>{t('home.openCanvas.title')}</h2>
        <p className={styles.sectionDescription}>{t('home.openCanvas.description')}</p>
        <div className={styles.canvasButtons}>
          <button
            type="button"
            onClick={handleOpenCharter}
            className={styles.canvasButton}
          >
            <span className={styles.canvasIcon}>
              <Icon semantic="artifact.document" decorative />
            </span>
            {t('home.openCanvas.charter')}
          </button>
          <button type="button" onClick={handleOpenWBS} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <Icon semantic="artifact.tree" decorative />
            </span>
            {t('home.openCanvas.wbs')}
          </button>
          <button
            type="button"
            onClick={handleOpenTimeline}
            className={styles.canvasButton}
          >
            <span className={styles.canvasIcon}>
              <Icon semantic="artifact.timeline" decorative />
            </span>
            {t('home.openCanvas.timeline')}
          </button>
          <button
            type="button"
            onClick={handleOpenSpreadsheet}
            className={styles.canvasButton}
          >
            <span className={styles.canvasIcon}>
              <Icon semantic="artifact.spreadsheet" decorative />
            </span>
            {t('home.openCanvas.spreadsheet')}
          </button>
          <button
            type="button"
            onClick={handleOpenDashboard}
            className={styles.canvasButton}
          >
            <span className={styles.canvasIcon}>
              <Icon semantic="artifact.dashboard" decorative />
            </span>
            {t('home.openCanvas.dashboard')}
          </button>
        </div>
      </section>

      <section className={styles.section} data-tour="home-quick-access">
        <h2 className={styles.sectionTitle}>{t('home.quickAccess')}</h2>
        <div className={styles.cardGrid}>
          {quickLinks.map((link) => (
            <Link key={link.path} to={link.path} className={styles.card}>
              <div className={styles.cardIcon}>
                <Icon semantic={link.icon} decorative size="lg" />
              </div>
              <h3 className={styles.cardTitle}>{link.title}</h3>
              <p className={styles.cardDescription}>{link.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.section} data-tour="home-configuration">
        <h2 className={styles.sectionTitle}>{t('home.configuration')}</h2>
        <div className={styles.linkList}>
          {configLinks.map((link) => (
            <Link key={link.path} to={link.path} className={styles.linkItem}>
              <div>
                <h3 className={styles.linkTitle}>{link.title}</h3>
                <p className={styles.linkDescription}>{link.description}</p>
              </div>
              <Icon semantic="navigation.next" decorative />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
