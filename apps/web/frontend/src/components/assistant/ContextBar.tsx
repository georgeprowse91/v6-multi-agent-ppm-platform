import { useState } from 'react';
import type { AssistantContext } from '@/store/assistant';
import styles from './ContextBar.module.css';

interface ContextBarProps {
  context: AssistantContext;
}

export function ContextBar({ context }: ContextBarProps) {
  const [expanded, setExpanded] = useState(false);

  const stageName = context.currentStageName ?? 'No stage selected';
  const activityName = context.currentActivityName ?? 'No activity selected';
  const stageProgress = Number.isFinite(context.stageProgress) ? context.stageProgress : 0;

  return (
    <section className={styles.contextBar} aria-label="Current context">
      <button
        type="button"
        className={styles.collapsedRow}
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        <span className={styles.breadcrumb} title={`${stageName} > ${activityName}`}>
          {stageName} &gt; {activityName}
        </span>
        <span className={styles.progressBadge}>{stageProgress}%</span>
      </button>

      {expanded && (
        <div className={styles.expandedContent}>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Project</span>
            <span className={styles.detailValue}>{context.projectName}</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Methodology</span>
            <span className={styles.detailValue}>{context.methodologyName}</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Stage progress</span>
            <span className={styles.detailValue}>{stageProgress}%</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Activity status</span>
            <span
              className={`${styles.detailValue} ${
                context.isCurrentActivityLocked ? styles.lockedValue : ''
              }`}
            >
              {context.isCurrentActivityLocked ? 'Locked' : 'Unlocked'}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
