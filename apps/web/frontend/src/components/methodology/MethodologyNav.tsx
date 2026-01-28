/**
 * MethodologyNav - Left panel navigation component for project methodology
 *
 * Features:
 * - Collapsible stages with activities
 * - Status icons (✓, ◐, ○, ⚠️, 🔒) and progress % per stage
 * - Stage-gate logic: locked stages/activities shown but not actionable
 * - "Monitoring & Controlling" section always accessible
 * - Clicking activity updates current activity and opens relevant canvas
 * - Integration with Assistant for context-aware suggestions
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMethodologyStore } from '@/store/methodology';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useAssistantStore } from '@/store/assistant';
import {
  STATUS_ICONS,
  STATUS_COLORS,
  type MethodologyActivity,
  type MethodologyStage,
  type MethodologyStatus,
} from '@/store/methodology';
import type { PrerequisiteInfo } from '@/store/assistant';
import { createArtifact, createEmptyContent, type CanvasType } from '@ppm/canvas-engine';
import styles from './MethodologyNav.module.css';

interface MethodologyNavProps {
  /** Whether the panel is collapsed (icon-only mode) */
  collapsed?: boolean;
}

export function MethodologyNav({ collapsed = false }: MethodologyNavProps) {
  const {
    projectMethodology,
    currentActivityId,
    expandedStageIds,
    setCurrentActivity,
    toggleStageExpanded,
    isStageLockedComputed,
    isActivityLockedComputed,
    getStageProgressComputed,
    getAllActivities,
    getStageForActivity,
  } = useMethodologyStore();

  const { openArtifact, artifacts } = useCanvasStore();
  const { showGatingWarning } = useAssistantStore();
  const navigate = useNavigate();

  const { methodology, projectName } = projectMethodology;

  // Helper to get incomplete prerequisites
  const getIncompletePrerequisites = useCallback(
    (activity: MethodologyActivity): PrerequisiteInfo[] => {
      const allActivitiesArray = getAllActivities();
      const result: PrerequisiteInfo[] = [];

      for (const prereqId of activity.prerequisites) {
        const prereq = allActivitiesArray.find((a) => a.id === prereqId);
        if (!prereq || prereq.status === 'complete') continue;

        const stage = getStageForActivity(prereqId);
        result.push({
          activityId: prereq.id,
          activityName: prereq.name,
          status: prereq.status as PrerequisiteInfo['status'],
          stageId: stage?.id ?? '',
          stageName: stage?.name ?? '',
        });
      }

      return result;
    },
    [getAllActivities, getStageForActivity]
  );

  const handleActivityClick = useCallback(
    (activity: MethodologyActivity, stageLocked: boolean) => {
      // Always allow setting current activity (for viewing)
      setCurrentActivity(activity.id);

      // If stage or activity is locked, user can view but not create artifacts
      const activityLocked = isActivityLockedComputed(activity.id);
      const isLocked = stageLocked || activityLocked;

      // If locked, show gating warning in assistant
      if (isLocked) {
        const incompletePrereqs = getIncompletePrerequisites(activity);
        if (incompletePrereqs.length > 0) {
          showGatingWarning(activity, incompletePrereqs);
        }
        return;
      }

      // Open the associated artifact if it exists, or create a new one
      if (activity.artifactId && artifacts[activity.artifactId]) {
        openArtifact(artifacts[activity.artifactId]);
      } else {
        // Create a new artifact for this activity
        const newArtifact = createArtifact(
          activity.canvasType,
          activity.name,
          projectMethodology.projectId,
          createEmptyContent(activity.canvasType)
        );
        openArtifact(newArtifact);
      }
    },
    [
      setCurrentActivity,
      isActivityLockedComputed,
      openArtifact,
      artifacts,
      projectMethodology.projectId,
      getIncompletePrerequisites,
      showGatingWarning,
    ]
  );

  const handleStageHeaderClick = useCallback(
    (stageId: string) => {
      toggleStageExpanded(stageId);
    },
    [toggleStageExpanded]
  );

  const handleCaptureLessons = useCallback(
    (stageId: string, stageName: string) => {
      const params = new URLSearchParams({
        projectId: projectMethodology.projectId,
        stageId,
        stageName,
      });
      navigate(`/knowledge/lessons?${params.toString()}`);
    },
    [navigate, projectMethodology.projectId]
  );

  return (
    <div className={styles.methodologyNav}>
      {!collapsed && (
        <div className={styles.projectHeader}>
          <span className={styles.projectLabel}>Project</span>
          <span className={styles.projectName}>{projectName}</span>
          <span className={styles.methodologyType}>{methodology.name}</span>
        </div>
      )}

      <nav className={styles.stageList} role="navigation" aria-label="Methodology navigation">
        {methodology.stages.map((stage) => (
          <StageItem
            key={stage.id}
            stage={stage}
            collapsed={collapsed}
            isExpanded={expandedStageIds.includes(stage.id)}
            isLocked={isStageLockedComputed(stage.id)}
            progress={getStageProgressComputed(stage.id)}
            currentActivityId={currentActivityId}
            isActivityLocked={isActivityLockedComputed}
            onStageClick={handleStageHeaderClick}
            onActivityClick={handleActivityClick}
            onCaptureLessons={handleCaptureLessons}
          />
        ))}
      </nav>
    </div>
  );
}

interface StageItemProps {
  stage: MethodologyStage;
  collapsed: boolean;
  isExpanded: boolean;
  isLocked: boolean;
  progress: number;
  currentActivityId: string | null;
  isActivityLocked: (activityId: string) => boolean;
  onStageClick: (stageId: string) => void;
  onActivityClick: (activity: MethodologyActivity, stageLocked: boolean) => void;
  onCaptureLessons: (stageId: string, stageName: string) => void;
}

function StageItem({
  stage,
  collapsed,
  isExpanded,
  isLocked,
  progress,
  currentActivityId,
  isActivityLocked,
  onStageClick,
  onActivityClick,
  onCaptureLessons,
}: StageItemProps) {
  // Compute effective status (locked overrides actual status for display)
  const displayStatus: MethodologyStatus = isLocked ? 'locked' : stage.status;

  return (
    <div
      className={`${styles.stageItem} ${isLocked ? styles.locked : ''} ${
        stage.alwaysAccessible ? styles.alwaysAccessible : ''
      }`}
    >
      <button
        className={styles.stageHeader}
        onClick={() => onStageClick(stage.id)}
        title={collapsed ? `${stage.name} (${progress}%)` : undefined}
        aria-expanded={isExpanded}
        aria-controls={`stage-activities-${stage.id}`}
      >
        <span className={styles.stageExpandIcon} aria-hidden="true">
          {isExpanded ? '▼' : '▶'}
        </span>
        <StatusIcon status={displayStatus} />
        {!collapsed && (
          <>
            <span className={styles.stageName}>{stage.name}</span>
            <span className={styles.stageProgress}>{progress}%</span>
            {stage.status === 'complete' && (
              <button
                className={styles.stageActionButton}
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onCaptureLessons(stage.id, stage.name);
                }}
              >
                Capture Lessons
              </button>
            )}
          </>
        )}
      </button>

      {isExpanded && !collapsed && (
        <ul
          id={`stage-activities-${stage.id}`}
          className={styles.activityList}
          role="list"
        >
          {stage.activities.map((activity) => (
            <ActivityItem
              key={activity.id}
              activity={activity}
              stageLocked={isLocked}
              isActivityLocked={isActivityLocked(activity.id)}
              isSelected={currentActivityId === activity.id}
              onClick={() => onActivityClick(activity, isLocked)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

interface ActivityItemProps {
  activity: MethodologyActivity;
  stageLocked: boolean;
  isActivityLocked: boolean;
  isSelected: boolean;
  onClick: () => void;
}

function ActivityItem({
  activity,
  stageLocked,
  isActivityLocked,
  isSelected,
  onClick,
}: ActivityItemProps) {
  // Compute effective status
  const isLocked = stageLocked || isActivityLocked;
  const displayStatus: MethodologyStatus = isLocked ? 'locked' : activity.status;

  return (
    <li className={styles.activityItem}>
      <button
        className={`${styles.activityButton} ${isSelected ? styles.selected : ''} ${
          isLocked ? styles.locked : ''
        } ${activity.alwaysAccessible ? styles.alwaysAccessible : ''}`}
        onClick={onClick}
        title={`${activity.name}${isLocked ? ' (Locked - prerequisites not met)' : ''}`}
        aria-current={isSelected ? 'true' : undefined}
      >
        <StatusIcon status={displayStatus} small />
        <span className={styles.activityName}>{activity.name}</span>
        <CanvasTypeIcon canvasType={activity.canvasType} />
      </button>
    </li>
  );
}

interface StatusIconProps {
  status: MethodologyStatus;
  small?: boolean;
}

function StatusIcon({ status, small = false }: StatusIconProps) {
  const icon = STATUS_ICONS[status];
  const color = STATUS_COLORS[status];

  return (
    <span
      className={`${styles.statusIcon} ${small ? styles.small : ''}`}
      style={{ color }}
      aria-label={status.replace('_', ' ')}
      role="img"
    >
      {icon}
    </span>
  );
}

interface CanvasTypeIconProps {
  canvasType: CanvasType;
}

function CanvasTypeIcon({ canvasType }: CanvasTypeIconProps) {
  const iconMap: Record<CanvasType, string> = {
    document: '📄',
    tree: '🌳',
    timeline: '📅',
    spreadsheet: '📊',
    dashboard: '📈',
  };

  return (
    <span className={styles.canvasTypeIcon} aria-hidden="true">
      {iconMap[canvasType]}
    </span>
  );
}

export default MethodologyNav;
