import { useMemo, useState } from 'react';
import type { ConversationalCommandMessageData } from '@/store/assistant';
import styles from './ConversationalCommandCard.module.css';

interface ConversationalCommandCardProps {
  data: ConversationalCommandMessageData;
  onCancel: () => void;
  onApply: (data: ConversationalCommandMessageData) => void;
}

function formatDiffValue(value?: string | number | null) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  return String(value);
}

export function ConversationalCommandCard({ data, onCancel, onApply }: ConversationalCommandCardProps) {
  const [confirmed, setConfirmed] = useState(false);

  const applyLabel = useMemo(() => data.applyLabel ?? 'Apply updates', [data.applyLabel]);

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <h3 className={styles.title}>{data.title}</h3>
      </header>

      {data.summary && <p className={styles.summary}>{data.summary}</p>}

      {data.changes.length === 0 ? (
        <p className={styles.summary}>No changes were provided for this conversational command.</p>
      ) : (
        <div className={styles.diffTable}>
          <div className={styles.diffHeader}>Field</div>
          <div className={styles.diffHeader}>Current</div>
          <div className={styles.diffHeader}>Proposed</div>
          {data.changes.map((change) => (
            <div key={change.id} className={styles.diffRow}>
              <div className={styles.diffCell}>
                <span className={styles.diffLabel}>{change.label}</span>
                {change.status && (
                  <span className={`${styles.diffBadge} ${styles[`diff${change.status}`]}`}>
                    {change.status}
                  </span>
                )}
              </div>
              <div className={styles.diffCell}>{formatDiffValue(change.before)}</div>
              <div className={styles.diffCell}>{formatDiffValue(change.after)}</div>
            </div>
          ))}
        </div>
      )}

      <label className={styles.confirmRow}>
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(event) => setConfirmed(event.target.checked)}
        />
        I understand these updates will change the canonical project records.
      </label>

      <div className={styles.actions}>
        <button type="button" className={styles.secondaryButton} onClick={onCancel}>
          Cancel
        </button>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => onApply(data)}
          disabled={!confirmed}
        >
          {applyLabel}
        </button>
      </div>
    </section>
  );
}
