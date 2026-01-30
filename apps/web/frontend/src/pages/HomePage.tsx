import { Link } from 'react-router-dom';
import { useCanvasStore, SAMPLE_ARTIFACT_IDS } from '@/store/useCanvasStore';
import styles from './HomePage.module.css';

const quickLinks = [
  {
    title: 'Portfolios',
    description: 'Manage strategic portfolios and investments',
    path: '/portfolio/demo',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    title: 'Programs',
    description: 'Coordinate related projects and initiatives',
    path: '/program/demo',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="currentColor">
        <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
      </svg>
    ),
  },
  {
    title: 'Projects',
    description: 'Execute and track individual projects',
    path: '/project/demo',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm2 10a1 1 0 10-2 0v3a1 1 0 102 0v-3zm2-3a1 1 0 011 1v5a1 1 0 11-2 0v-5a1 1 0 011-1zm4-1a1 1 0 10-2 0v7a1 1 0 102 0V8z"
          clipRule="evenodd"
        />
      </svg>
    ),
  },
];

const configLinks = [
  {
    title: 'Agents',
    description: 'Configure AI agents and their capabilities',
    path: '/config/agents',
  },
  {
    title: 'Connectors',
    description: 'Manage integrations with external systems',
    path: '/config/connectors',
  },
  {
    title: 'Workflows',
    description: 'Adjust workflow routing and orchestration settings',
    path: '/config/workflows',
  },
];

export function HomePage() {
  const { artifacts, openArtifact } = useCanvasStore();

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
      <header className={styles.header}>
        <h1 className={styles.title}>Welcome to PPM Platform</h1>
        <p className={styles.subtitle}>
          Multi-agent project, program, and portfolio management
        </p>
      </header>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Open Canvas</h2>
        <p className={styles.sectionDescription}>
          Try the new Canvas framework with multi-tab management
        </p>
        <div className={styles.canvasButtons}>
          <button onClick={handleOpenCharter} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </span>
            Open Charter (Doc)
          </button>
          <button onClick={handleOpenWBS} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="6" y1="3" x2="6" y2="15" />
                <circle cx="18" cy="6" r="3" />
                <circle cx="6" cy="18" r="3" />
                <path d="M18 9a9 9 0 0 1-9 9" />
              </svg>
            </span>
            Open WBS (Tree)
          </button>
          <button onClick={handleOpenTimeline} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            </span>
            Open Timeline
          </button>
          <button onClick={handleOpenSpreadsheet} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="9" x2="21" y2="9" />
                <line x1="3" y1="15" x2="21" y2="15" />
                <line x1="9" y1="3" x2="9" y2="21" />
                <line x1="15" y1="3" x2="15" y2="21" />
              </svg>
            </span>
            Open Spreadsheet
          </button>
          <button onClick={handleOpenDashboard} className={styles.canvasButton}>
            <span className={styles.canvasIcon}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="9" />
                <rect x="14" y="3" width="7" height="5" />
                <rect x="14" y="12" width="7" height="9" />
                <rect x="3" y="16" width="7" height="5" />
              </svg>
            </span>
            Open Dashboard
          </button>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Quick Access</h2>
        <div className={styles.cardGrid}>
          {quickLinks.map((link) => (
            <Link key={link.path} to={link.path} className={styles.card}>
              <div className={styles.cardIcon}>{link.icon}</div>
              <h3 className={styles.cardTitle}>{link.title}</h3>
              <p className={styles.cardDescription}>{link.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Configuration</h2>
        <div className={styles.linkList}>
          {configLinks.map((link) => (
            <Link key={link.path} to={link.path} className={styles.linkItem}>
              <div>
                <h3 className={styles.linkTitle}>{link.title}</h3>
                <p className={styles.linkDescription}>{link.description}</p>
              </div>
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
