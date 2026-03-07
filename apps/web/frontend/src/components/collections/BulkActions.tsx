import { useCallback, useState } from 'react';
import styles from './BulkActions.module.css';

export interface BulkAction {
  /** Unique action key */
  key: string;
  /** Display label */
  label: string;
  /** Visual variant */
  variant?: 'default' | 'primary' | 'danger';
  /** Whether to show confirmation dialog */
  confirm?: boolean;
  /** Confirmation message */
  confirmMessage?: string;
}

export interface BulkActionsProps {
  /** Number of selected items */
  selectedCount: number;
  /** Available bulk actions */
  actions: BulkAction[];
  /** Callback when an action is executed */
  onAction: (actionKey: string) => void;
  /** Callback to clear selection */
  onClearSelection: () => void;
  /** Entity type label */
  entityLabel?: string;
}

export function BulkActions({
  selectedCount,
  actions,
  onAction,
  onClearSelection,
  entityLabel = 'items',
}: BulkActionsProps) {
  const [confirmAction, setConfirmAction] = useState<BulkAction | null>(null);

  const handleAction = useCallback(
    (action: BulkAction) => {
      if (action.confirm) {
        setConfirmAction(action);
      } else {
        onAction(action.key);
      }
    },
    [onAction],
  );

  const confirmExecution = useCallback(() => {
    if (confirmAction) {
      onAction(confirmAction.key);
      setConfirmAction(null);
    }
  }, [confirmAction, onAction]);

  if (selectedCount === 0) return null;

  return (
    <>
      <div className={styles.bar}>
        <span className={styles.selectionCount}>
          {selectedCount} {entityLabel} selected
        </span>
        <div className={styles.actions}>
          {actions.map((action) => {
            let btnClass = styles.actionBtn;
            if (action.variant === 'primary') btnClass += ` ${styles.actionBtnPrimary}`;
            if (action.variant === 'danger') btnClass += ` ${styles.actionBtnDanger}`;
            return (
              <button
                key={action.key}
                type="button"
                className={btnClass}
                onClick={() => handleAction(action)}
              >
                {action.label}
              </button>
            );
          })}
        </div>
        <button type="button" className={styles.clearBtn} onClick={onClearSelection}>
          Clear selection
        </button>
      </div>

      {confirmAction && (
        <div className={styles.confirmOverlay} onClick={() => setConfirmAction(null)}>
          <div className={styles.confirmDialog} onClick={(e) => e.stopPropagation()}>
            <div className={styles.confirmTitle}>Confirm action</div>
            <div className={styles.confirmMessage}>
              {confirmAction.confirmMessage ||
                `Are you sure you want to ${confirmAction.label.toLowerCase()} ${selectedCount} ${entityLabel}?`}
            </div>
            <div className={styles.confirmActions}>
              <button
                type="button"
                className={styles.actionBtn}
                onClick={() => setConfirmAction(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className={
                  confirmAction.variant === 'danger'
                    ? `${styles.actionBtn} ${styles.actionBtnDanger}`
                    : `${styles.actionBtn} ${styles.actionBtnPrimary}`
                }
                onClick={confirmExecution}
              >
                {confirmAction.label}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default BulkActions;
