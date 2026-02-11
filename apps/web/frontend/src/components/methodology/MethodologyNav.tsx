/**
 * MethodologyNav - Left panel navigation component for project methodology
 *
 * Features:
 * - Collapsible stages with activities
 * - Status icons and progress bar per stage
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
  type MethodologyActivity,
  type MethodologyStage,
  type MethodologyStatus,
} from '@/store/methodology';
import type { PrerequisiteInfo } from '@/store/assistant';
import { createArtifact, createEmptyContent, type CanvasType } from '@ppm/canvas-engine';
import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './MethodologyNav.module.css';


interface ActivityRenderNode {
  activity: MethodologyActivity;
  depth: 0 | 1;
  parentId?: string;
}

function flattenActivityTree(
  activities: MethodologyActivity[],
  depth: 0 | 1 = 0,
  parentId?: string
): ActivityRenderNode[] {
  return activities.flatMap((activity) => {
    const node: ActivityRenderNode = { activity, depth, parentId };

    if (!activity.children?.length || depth >= 1) {
      return [node];
    }

    return [node, ...flattenActivityTree(activity.children, 1, activity.id)];
  });
}

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
  const stageNameLookup = Object.fromEntries(
    methodology.stages.map((stage) => [stage.id, stage.name])
  );

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
            stageNameLookup={stageNameLookup}
            currentActivityId={currentActivityId}
            isActivityLocked={isActivityLockedComputed}
            getIncompletePrerequisites={getIncompletePrerequisites}
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
  stageNameLookup: Record<string, string>;
  currentActivityId: string | null;
  isActivityLocked: (activityId: string) => boolean;
  getIncompletePrerequisites: (activity: MethodologyActivity) => PrerequisiteInfo[];
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
  stageNameLookup,
  currentActivityId,
  isActivityLocked,
  getIncompletePrerequisites,
  onStageClick,
  onActivityClick,
  onCaptureLessons,
}: StageItemProps) {
  // Compute effective status (locked overrides actual status for display)
  const displayStatus: MethodologyStatus = isLocked ? 'locked' : stage.status;
  const progressTone = getProgressTone(displayStatus);
  const prerequisiteNames = stage.prerequisites
    .map((prereqId) => stageNameLookup[prereqId])
    .filter(Boolean);
  const gateCriteria = prerequisiteNames.length
    ? `Gate criteria: prerequisites completed (${prerequisiteNames.join(
        ', '
      )}), approvals received.`
    : 'Gate criteria: approvals received, readiness checklist complete.';
  const activityNodes = flattenActivityTree(stage.activities);

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
            <span className={styles.stageProgressWrapper}>
              <span
                className={styles.stageProgressBar}
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${stage.name} progress`}
              >
                <span
                  className={`${styles.stageProgressFill} ${styles[progressTone]}`}
                  style={{ width: `${progress}%` }}
                />
              </span>
              <span className={styles.stageGateTooltip}>{gateCriteria}</span>
            </span>
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
          {activityNodes.map(({ activity, depth, parentId }) => {
            const childCount = activity.children?.length ?? 0;
            const groupLabel =
              depth === 0 && childCount > 0
                ? `${activity.name} group (${childCount} item${childCount === 1 ? '' : 's'})`
                : undefined;

            return (
              <ActivityItem
                key={activity.id}
                activity={activity}
                stageLocked={isLocked}
                isActivityLocked={isActivityLocked(activity.id)}
                missingPrerequisites={getIncompletePrerequisites(activity)}
                isSelected={currentActivityId === activity.id}
                depth={depth}
                parentId={parentId}
                groupLabel={groupLabel}
                onClick={() => onActivityClick(activity, isLocked)}
              />
            );
          })}
        </ul>
      )}
    </div>
  );
}

interface ActivityItemProps {
  activity: MethodologyActivity;
  stageLocked: boolean;
  isActivityLocked: boolean;
  missingPrerequisites: PrerequisiteInfo[];
  isSelected: boolean;
  depth?: 0 | 1;
  parentId?: string;
  groupLabel?: string;
  onClick: () => void;
}

function ActivityItem({
  activity,
  stageLocked,
  isActivityLocked,
  missingPrerequisites,
  isSelected,
  depth = 0,
  parentId,
  groupLabel,
  onClick,
}: ActivityItemProps) {
  // Compute effective status
  const isLocked = stageLocked || isActivityLocked;
  const displayStatus: MethodologyStatus = isLocked ? 'locked' : activity.status;
  const missingLabel = missingPrerequisites.length
    ? missingPrerequisites.map((prereq) => prereq.activityName).join(', ')
    : 'Additional prerequisites required.';

  return (
    <li
      className={`${styles.activityItem} ${depth === 1 ? styles.nestedActivityItem : ''}`}
      role="listitem"
      aria-level={depth + 1}
    >
      <button
        className={`${styles.activityButton} ${isSelected ? styles.selected : ''} ${
          isLocked ? styles.locked : ''
        } ${activity.alwaysAccessible ? styles.alwaysAccessible : ''} ${
          depth === 1 ? styles.nestedActivityButton : ''
        }`}
        onClick={onClick}
        title={`${activity.name}${isLocked ? ' (Locked - prerequisites not met)' : ''}`}
        aria-current={isSelected ? 'true' : undefined}
        aria-describedby={groupLabel ? `${activity.id}-group-label` : undefined}
        data-parent-id={parentId}
      >
        <StatusIcon status={displayStatus} small />
        <span className={styles.activityName}>{activity.name}</span>
        {groupLabel && (
          <span id={`${activity.id}-group-label`} className={styles.activityGroupLabel}>
            {groupLabel}
          </span>
        )}
        <CanvasTypeIcon canvasType={activity.canvasType} />
      </button>
      {isLocked && (
        <div className={styles.lockedPopover} role="tooltip">
          <div className={styles.lockedPopoverTitle}>Missing prerequisites</div>
          {missingPrerequisites.length > 0 ? (
            <ul className={styles.lockedPopoverList}>
              {missingPrerequisites.map((prereq) => (
                <li key={prereq.activityId}>
                  {prereq.activityName} ({prereq.stageName})
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.lockedPopoverText}>{missingLabel}</p>
          )}
        </div>
      )}
    </li>
  );
}

interface StatusIconProps {
  status: MethodologyStatus;
  small?: boolean;
}

function StatusIcon({ status, small = false }: StatusIconProps) {
  const icon = STATUS_ICONS[status];

  return (
    <Icon
      semantic={icon}
      label={status.replace('_', ' ')}
      className={`${styles.statusIcon} ${small ? styles.small : ''}`}
      size={small ? 'sm' : 'md'}
    />
  );
}

interface CanvasTypeIconProps {
  canvasType: CanvasType;
}

function CanvasTypeIcon({ canvasType }: CanvasTypeIconProps) {
  const iconMap: Record<CanvasType, IconSemantic> = {
    document: 'artifact.document',
    tree: 'artifact.tree',
    timeline: 'artifact.timeline',
    spreadsheet: 'artifact.spreadsheet',
    dashboard: 'artifact.dashboard',
  };

  return (
    <Icon
      semantic={iconMap[canvasType]}
      decorative
      className={styles.canvasTypeIcon}
      size="sm"
    />
  );
}

type ProgressTone = 'onTrack' | 'atRisk' | 'offTrack';

function getProgressTone(status: MethodologyStatus): ProgressTone {
  if (status === 'locked') {
    return 'offTrack';
  }

  if (status === 'blocked') {
    return 'atRisk';
  }

  return 'onTrack';
}

export default MethodologyNav;
