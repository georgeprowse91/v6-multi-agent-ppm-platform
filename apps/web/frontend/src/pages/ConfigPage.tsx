import { AgentGallery } from '@/components/agentConfig';
import styles from './ConfigPage.module.css';

type ConfigType = 'agents' | 'connectors' | 'templates';

interface ConfigPageProps {
  type: ConfigType;
}

const configInfo: Record<
  ConfigType,
  { title: string; description: string; features: string[] }
> = {
  agents: {
    title: 'AI Agents',
    description:
      'Configure and manage the AI agents that power your PPM workflows.',
    features: [
      'View available agents and their capabilities',
      'Configure agent parameters and thresholds',
      'Monitor agent performance and activity',
      'Manage agent permissions and access',
    ],
  },
  connectors: {
    title: 'Connectors',
    description:
      'Manage integrations with external systems and data sources.',
    features: [
      'Connect to project management tools (Jira, Azure DevOps, etc.)',
      'Integrate with enterprise systems (ServiceNow, SAP)',
      'Configure data synchronization schedules',
      'Monitor connection health and status',
    ],
  },
  templates: {
    title: 'Templates',
    description:
      'Define reusable templates for projects, programs, and workflows.',
    features: [
      'Create project templates with predefined phases',
      'Define workflow templates for common processes',
      'Set up document templates and standards',
      'Share templates across the organization',
    ],
  },
};

export function ConfigPage({ type }: ConfigPageProps) {
  const info = configInfo[type];

  // Render AgentGallery for agents type
  if (type === 'agents') {
    return <AgentGallery />;
  }

  // Placeholder for other config types
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{info.title}</h1>
        <p className={styles.description}>{info.description}</p>
      </header>

      <div className={styles.content}>
        <section className={styles.placeholder}>
          <svg
            className={styles.placeholderIcon}
            width="64"
            height="64"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.placeholderTitle}>
            {info.title} Configuration
          </h2>
          <p className={styles.placeholderDescription}>
            This configuration page is under development.
          </p>
        </section>

        <section className={styles.features}>
          <h3 className={styles.featuresTitle}>Planned Features</h3>
          <ul className={styles.featureList}>
            {info.features.map((feature, index) => (
              <li key={index} className={styles.featureItem}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className={styles.featureIcon}
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                {feature}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
