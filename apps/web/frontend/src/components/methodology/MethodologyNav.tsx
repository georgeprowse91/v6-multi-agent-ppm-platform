import { useCallback } from 'react';
import { requestJson } from '@/services/apiClient';
import { useMethodologyStore } from '@/store/methodology';
import { STATUS_ICONS, flattenMethodologyActivities, type MethodologyActivity, type MethodologyStatus } from '@/store/methodology';
import { Icon } from '@/components/icon/Icon';
import styles from './MethodologyNav.module.css';

interface MethodologyNavProps {
  collapsed?: boolean;
}

export function MethodologyNav({ collapsed = false }: MethodologyNavProps) {
  const {
    projectMethodology,
    currentActivityId,
    expandedStageIds,
    setCurrentActivity,
    toggleStageExpanded,
    resolveNodeRuntime,
    isStageLockedComputed,
    isActivityLockedComputed,
  } = useMethodologyStore();

  const onSelect = useCallback(async (activity: MethodologyActivity, stageId: string) => {
    setCurrentActivity(activity.id);
    await requestJson(`/api/workspace/${encodeURIComponent(projectMethodology.projectId)}/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_stage_id: stageId === 'monitoring' ? null : stageId, current_activity_id: activity.id }),
    });
    await resolveNodeRuntime({ methodologyId: projectMethodology.methodology.id, stageId, activityId: activity.id, event: 'view' });
  }, [projectMethodology.methodology.id, projectMethodology.projectId, resolveNodeRuntime, setCurrentActivity]);

  return (
    <div className={styles.methodologyNav}>
      <nav className={styles.stageList}>
        {projectMethodology.methodology.stages.map((stage) => {
          const locked = isStageLockedComputed(stage.id);
          const expanded = expandedStageIds.includes(stage.id);
          return (
            <div key={stage.id} className={styles.stageItem}>
              <button type="button" className={styles.stageHeader} onClick={() => toggleStageExpanded(stage.id)}>
                <span className={styles.stageExpandIcon}>{expanded ? '▼' : '▶'}</span>
                <StatusIcon status={locked ? 'locked' : stage.status} />
                {!collapsed && <span className={styles.stageName}>{stage.name}</span>}
              </button>
              {expanded && !collapsed && (
                <ul className={styles.activityList}>
                  {flattenMethodologyActivities(stage.activities).map((activity) => {
                    const activityLocked = locked || isActivityLockedComputed(activity.id);
                    return (
                      <li key={activity.id} className={styles.activityItem}>
                        <button
                          type="button"
                          className={`${styles.activityButton} ${currentActivityId === activity.id ? styles.selected : ''}`}
                          onClick={() => { void onSelect(activity, stage.id); }}
                          title={activityLocked ? 'Blocked by prerequisites' : undefined}
                        >
                          <StatusIcon status={activityLocked ? 'locked' : activity.status} small />
                          <span className={styles.activityName}>{activity.name}</span>
                          <Icon semantic="artifact.document" decorative className={styles.canvasTypeIcon} size="sm" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
        {!collapsed && projectMethodology.methodology.monitoring.length > 0 && (
          <div className={styles.stageItem}>
            <button type="button" className={styles.stageHeader}>
              <span className={styles.stageExpandIcon}>•</span>
              <StatusIcon status="in_progress" />
              <span className={styles.stageName}>Monitoring &amp; Controlling</span>
            </button>
            <ul className={styles.activityList}>
              {projectMethodology.methodology.monitoring.map((activity) => (
                <li key={activity.id} className={styles.activityItem}>
                  <button
                    type="button"
                    className={`${styles.activityButton} ${currentActivityId === activity.id ? styles.selected : ''}`}
                    onClick={() => { void onSelect(activity, 'monitoring'); }}
                  >
                    <StatusIcon status={activity.status} small />
                    <span className={styles.activityName}>{activity.name}</span>
                    <Icon semantic="artifact.dashboard" decorative className={styles.canvasTypeIcon} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

      </nav>
    </div>
  );
}

function StatusIcon({ status, small = false }: { status: MethodologyStatus; small?: boolean }) {
  return <Icon semantic={STATUS_ICONS[status]} label={status} className={`${styles.statusIcon} ${small ? styles.small : ''}`} size={small ? 'sm' : 'md'} />;
}

export default MethodologyNav;
