/**
 * Methodology Map Types - Data model for project methodology navigation
 *
 * Supports various methodologies: Waterfall, Agile, Hybrid, etc.
 * Extensible for templates and custom methodologies.
 */

import type { CanvasType } from '@ppm/canvas-engine';
import type { IconSemantic } from '@/components/icon/iconMap';

/**
 * Status of a stage or activity
 */
export type MethodologyStatus =
  | 'not_started'  // Has not begun
  | 'in_progress'  // Currently being worked on
  | 'complete'     // Finished
  | 'blocked'      // Blocked by issues/risks
  | 'locked';      // Prerequisites not met (computed)

/**
 * Type of methodology template
 */
export type MethodologyType = 'waterfall' | 'agile' | 'hybrid' | 'custom';

/**
 * An activity within a stage
 */
export interface MethodologyActivity {
  /** Unique identifier */
  id: string;

  /** Display name */
  name: string;

  /** Brief description */
  description?: string;

  /** Current status */
  status: MethodologyStatus;

  /** Canvas type this activity produces (for opening the right canvas) */
  canvasType: CanvasType;

  /** Associated artifact ID if one exists */
  artifactId?: string;

  /** Activity IDs that must be complete before this one can start */
  prerequisites: string[];

  /** Whether this activity is always accessible (e.g., monitoring activities) */
  alwaysAccessible?: boolean;

  /** Optional icon name */
  icon?: IconSemantic;

  /** Order within the stage */
  order: number;

  /** Optional extensible metadata (e.g., sprint or release semantics) */
  metadata?: Record<string, unknown>;

  /**
   * Optional child activities used for one extra hierarchy level
   * (e.g., sprint groups with nested sprint activities, nested iterations, milestone gates).
   */
  children?: MethodologyActivity[];
}

/**
 * A stage (phase) in the methodology
 */
export interface MethodologyStage {
  /** Unique identifier */
  id: string;

  /** Display name */
  name: string;

  /** Brief description */
  description?: string;

  /** Current status (computed from activities or manually set) */
  status: MethodologyStatus;

  /** Activities within this stage */
  activities: MethodologyActivity[];

  /** Stage IDs that must be complete before this one can start */
  prerequisites: string[];

  /** Whether this stage is always accessible (e.g., "Monitoring & Controlling") */
  alwaysAccessible?: boolean;

  /** Optional icon name */
  icon?: IconSemantic;

  /** Order in the methodology */
  order: number;

  /** Optional extensible metadata (e.g., execution model or release gates) */
  metadata?: Record<string, unknown>;

  /**
   * Optional child stages for extended hierarchy modeling.
   * Current navigation renders stage -> activity -> child activity.
   */
  children?: MethodologyStage[];
}

/**
 * Complete methodology definition
 */
export interface MethodologyMap {
  /** Unique identifier */
  id: string;

  /** Display name (e.g., "Waterfall", "Agile Scrum", "Hybrid") */
  name: string;

  /** Description of this methodology */
  description?: string;

  /** Type categorization */
  type: MethodologyType;

  /** Stages in this methodology */
  stages: MethodologyStage[];

  /** Version for template updates */
  version: string;
}

/**
 * Project methodology instance - ties a project to a methodology with state
 */
export interface ProjectMethodology {
  /** Project ID */
  projectId: string;

  /** Project name for display */
  projectName: string;

  /** The methodology being used */
  methodology: MethodologyMap;

  /** Currently selected activity ID */
  currentActivityId: string | null;

  /** Currently expanded stage IDs */
  expandedStageIds: string[];
}

/**
 * Icon mapping for status display
 */
export const STATUS_ICONS: Record<MethodologyStatus, IconSemantic> = {
  not_started: 'status.notStarted',
  in_progress: 'status.inProgress',
  complete: 'status.success',
  blocked: 'status.warning',
  locked: 'status.locked',
};

/**
 * Color mapping for status display
 */
export const STATUS_COLORS: Record<MethodologyStatus, string> = {
  not_started: 'var(--color-neutral-grey-400)',
  in_progress: 'var(--color-neutral-grey-500)',
  complete: 'var(--color-state-success-fg)',
  blocked: 'var(--color-state-warning-fg)',
  locked: 'var(--color-neutral-grey-300)',
};

/**
 * Flatten activities including one-level-or-deeper nested child activities
 */

export function flattenMethodologyActivities(
  activities: MethodologyActivity[]
): MethodologyActivity[] {
  return activities.flatMap((activity) => {
    if (!activity.children?.length) {
      return [activity];
    }

    return [activity, ...flattenMethodologyActivities(activity.children)];
  });
}

/**
 * Calculate progress percentage for a stage based on activity statuses
 */
export function calculateStageProgress(stage: MethodologyStage): number {
  const activities = flattenMethodologyActivities(stage.activities);
  if (activities.length === 0) return 0;

  const completedCount = activities.filter(a => a.status === 'complete').length;
  const inProgressCount = activities.filter(a => a.status === 'in_progress').length;

  // In progress counts as 50% done
  const progressValue = completedCount + (inProgressCount * 0.5);
  return Math.round((progressValue / activities.length) * 100);
}

/**
 * Determine computed status for a stage based on its activities
 */
export function computeStageStatus(stage: MethodologyStage): MethodologyStatus {
  const activities = flattenMethodologyActivities(stage.activities);
  if (activities.length === 0) return 'not_started';

  const statuses = activities.map(a => a.status);

  // If any activity is blocked, stage is blocked
  if (statuses.some(s => s === 'blocked')) return 'blocked';

  // If all complete, stage is complete
  if (statuses.every(s => s === 'complete')) return 'complete';

  // If any in progress, stage is in progress
  if (statuses.some(s => s === 'in_progress')) return 'in_progress';

  // If any complete but not all, stage is in progress
  if (statuses.some(s => s === 'complete')) return 'in_progress';

  return 'not_started';
}

/**
 * Check if an activity is locked based on prerequisites
 */
export function isActivityLocked(
  activity: MethodologyActivity,
  allActivities: MethodologyActivity[]
): boolean {
  if (activity.alwaysAccessible) return false;
  if (activity.prerequisites.length === 0) return false;

  return activity.prerequisites.some(prereqId => {
    const prereq = allActivities.find(a => a.id === prereqId);
    return prereq && prereq.status !== 'complete';
  });
}

/**
 * Check if a stage is locked based on prerequisites
 */
export function isStageLocked(
  stage: MethodologyStage,
  allStages: MethodologyStage[]
): boolean {
  if (stage.alwaysAccessible) return false;
  if (stage.prerequisites.length === 0) return false;

  return stage.prerequisites.some(prereqId => {
    const prereqStage = allStages.find(s => s.id === prereqId);
    return prereqStage && computeStageStatus(prereqStage) !== 'complete';
  });
}
