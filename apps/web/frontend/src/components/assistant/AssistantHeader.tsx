import { Icon } from '@/components/icon/Icon';
import type { AIState } from '@/store/assistant/types';
import styles from './AssistantHeader.module.css';

interface AssistantHeaderProps {
  title: string;
  aiState: AIState;
  toggleRightPanel: () => void;
  onClose?: () => void;
  onCollapse?: () => void;
}

const ERROR_STATES: AIState[] = ['error', 'refusal', 'uncertain'];

export function AssistantHeader({
  title,
  aiState,
  toggleRightPanel,
  onClose,
  onCollapse,
}: AssistantHeaderProps) {
  const showErrorState = ERROR_STATES.includes(aiState);

  const handleCollapse = () => {
    onCollapse?.();
    onClose?.();
    toggleRightPanel();
  };

  return (
    <div className={styles.header}>
      <h2 className={styles.title}>{title}</h2>
      {showErrorState && (
        <div className={styles.aiState} aria-live="polite">
          <span className={styles.aiStateIndicator} data-state={aiState} />
          <span className={styles.aiStateLabel}>{aiState.replace(/_/g, ' ')}</span>
        </div>
      )}
      <button
        className={styles.collapseButton}
        onClick={handleCollapse}
        title="Close Assistant"
      >
        <Icon
          semantic="actions.cancelDismiss"
          label="Close Assistant"
        />
      </button>
    </div>
  );
}
