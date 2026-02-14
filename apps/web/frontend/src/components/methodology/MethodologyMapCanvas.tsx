import { Icon } from '@/components/icon/Icon';
import type { MethodologyActivity, MethodologyStage } from '@/store/methodology';
import styles from './MethodologyMapCanvas.module.css';

interface TemplateBinding {
  methodology_bindings: Array<{ activity_id: string }>;
}

interface MethodologyMapCanvasProps {
  stages: MethodologyStage[];
  monitoring: MethodologyActivity[];
  currentActivityId: string | null;
  isStageLockedComputed: (stageId: string) => boolean;
  isActivityLockedComputed: (activityId: string) => boolean;
  templatesRequiredHere: TemplateBinding[];
  templatesInReview: TemplateBinding[];
  onSelectActivity: (activity: MethodologyActivity, stageId: string) => void;
}

function countTemplates(items: TemplateBinding[], activityId: string): number {
  return items.filter((template) =>
    template.methodology_bindings.some((binding) => binding.activity_id === activityId)
  ).length;
}

function flattenCards(activities: MethodologyActivity[]): MethodologyActivity[] {
  return activities.flatMap((activity) => [activity, ...flattenCards(activity.children ?? [])]);
}

export function MethodologyMapCanvas({
  stages,
  monitoring,
  currentActivityId,
  isStageLockedComputed,
  isActivityLockedComputed,
  templatesRequiredHere,
  templatesInReview,
  onSelectActivity,
}: MethodologyMapCanvasProps) {
  const orderedMonitoring = [...monitoring].sort((a, b) => {
    const aDashboard = a.name.toLowerCase().includes('performance') || a.canvasType === 'dashboard';
    const bDashboard = b.name.toLowerCase().includes('performance') || b.canvasType === 'dashboard';
    if (aDashboard && !bDashboard) return -1;
    if (!aDashboard && bDashboard) return 1;
    return a.order - b.order;
  });

  return (
    <section className={styles.canvas}>
      <div className={styles.stageGrid}>
        {stages.map((stage) => {
          const stageLocked = isStageLockedComputed(stage.id);
          return (
            <div key={stage.id} className={styles.stageColumn}>
              <header className={styles.stageHeader}>
                <span>{stage.name}</span>
                {stageLocked && <Icon semantic="status.locked" label="Stage locked" size="sm" />}
              </header>
              <div className={styles.cards}>
                {flattenCards(stage.activities).map((activity) => {
                  const activityLocked = stageLocked || isActivityLockedComputed(activity.id);
                  const requiredCount = countTemplates(templatesRequiredHere, activity.id);
                  const inReviewCount = countTemplates(templatesInReview, activity.id);
                  return (
                    <button
                      key={activity.id}
                      type="button"
                      className={`${styles.card} ${currentActivityId === activity.id ? styles.selected : ''}`}
                      onClick={() => onSelectActivity(activity, stage.id)}
                    >
                      <span className={styles.cardTitle}>{activity.name}</span>
                      <span className={styles.meta}>{activity.status.replace('_', ' ')}</span>
                      {activityLocked && <span className={styles.meta}>Locked</span>}
                      <span className={styles.meta}>Required templates: {requiredCount}</span>
                      <span className={styles.meta}>In review: {inReviewCount}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.monitoringBand}>
        <h3>Monitoring &amp; Controlling (cross-cutting)</h3>
        <div className={styles.monitoringRow}>
          {orderedMonitoring.map((activity, index) => (
            <button
              key={activity.id}
              type="button"
              className={`${styles.card} ${styles.monitoringCard} ${index === 0 ? styles.dashboardCard : ''} ${currentActivityId === activity.id ? styles.selected : ''}`}
              onClick={() => onSelectActivity(activity, 'monitoring')}
            >
              <span className={styles.cardTitle}>{activity.name}</span>
              <span className={styles.meta}>{activity.status.replace('_', ' ')}</span>
              <span className={styles.meta}>Always accessible</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
