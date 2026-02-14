import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './EmptyState.module.css';

type EmptyStateIcon =
  | 'dashboard'
  | 'timeline'
  | 'search'
  | 'confirm'
  | 'agents'
  | 'connectors'
  | 'workflow';

type EmptyStateAction = {
  label: string;
  onClick?: () => void;
  href?: string;
};

interface EmptyStateProps {
  icon: EmptyStateIcon;
  title: string;
  description: string;
  action?: EmptyStateAction;
  className?: string;
}

const iconSemanticMap: Record<EmptyStateIcon, IconSemantic> = {
  dashboard: 'artifact.dashboard',
  timeline: 'artifact.timeline',
  search: 'navigation.search',
  confirm: 'actions.confirmApply',
  agents: 'communication.assistant',
  connectors: 'connectors.cpuChip',
  workflow: 'artifact.tree',
};

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  const rootClassName = [styles.emptyState, className].filter(Boolean).join(' ');

  return (
    <div className={rootClassName}>
      <div className={styles.iconWrap}>
        <Icon semantic={iconSemanticMap[icon]} decorative size="xl" />
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.description}>{description}</p>
      {action &&
        (action.href ? (
          <a href={action.href} className={styles.actionButton}>
            {action.label}
          </a>
        ) : (
          <button type="button" className={styles.actionButton} onClick={action.onClick}>
            {action.label}
          </button>
        ))}
    </div>
  );
}
