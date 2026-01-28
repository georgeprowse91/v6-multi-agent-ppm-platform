/**
 * Assistant Types - Data model for the AI assistant panel
 *
 * Supports:
 * - Chat messages with different roles
 * - Next Best Action chips with categories
 * - Context-aware suggestions based on methodology state
 */

import type { CanvasType } from '@ppm/canvas-engine';

/**
 * Message roles in the assistant chat
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Categories for action chips
 */
export type ActionCategory =
  | 'create'    // Create new content/artifacts
  | 'review'    // Review existing content
  | 'approve'   // Approval actions
  | 'analyse'   // Analysis tasks
  | 'navigate'; // Navigate to different activities/stages

/**
 * Priority levels for action chips
 */
export type ActionPriority = 'high' | 'medium' | 'low';

/**
 * Type of action a chip can trigger
 */
export type ActionType =
  | 'open_activity'      // Navigate to an activity
  | 'open_artifact'      // Open a specific artifact
  | 'open_dashboard'     // Open the project dashboard
  | 'generate_template'  // Generate content based on context
  | 'show_prerequisites' // Show what's blocking
  | 'complete_activity'  // Mark activity as complete
  | 'custom';            // Custom action with callback

/**
 * An action chip that suggests a next best action
 */
export interface ActionChip {
  /** Unique identifier */
  id: string;

  /** Display label */
  label: string;

  /** Category for styling and grouping */
  category: ActionCategory;

  /** Priority for ordering */
  priority: ActionPriority;

  /** Icon (emoji or icon name) */
  icon?: string;

  /** Type of action */
  actionType: ActionType;

  /** Action payload (depends on actionType) */
  payload: ActionPayload;

  /** Whether this chip is currently enabled */
  enabled: boolean;

  /** Optional tooltip/description */
  description?: string;
}

/**
 * Payload for different action types
 */
export type ActionPayload =
  | OpenActivityPayload
  | OpenArtifactPayload
  | OpenDashboardPayload
  | GenerateTemplatePayload
  | ShowPrerequisitesPayload
  | CompleteActivityPayload
  | CustomActionPayload;

export interface OpenActivityPayload {
  type: 'open_activity';
  activityId: string;
  stageId?: string;
}

export interface OpenArtifactPayload {
  type: 'open_artifact';
  artifactId: string;
}

export interface OpenDashboardPayload {
  type: 'open_dashboard';
}

export interface GenerateTemplatePayload {
  type: 'generate_template';
  templateType: string;
  basedOn?: string[]; // Activity IDs to base the template on
  targetActivityId: string;
}

export interface ShowPrerequisitesPayload {
  type: 'show_prerequisites';
  activityId: string;
  prerequisiteIds: string[];
}

export interface CompleteActivityPayload {
  type: 'complete_activity';
  activityId: string;
}

export interface CustomActionPayload {
  type: 'custom';
  actionKey: string;
  data?: Record<string, unknown>;
}

/**
 * An assistant chat message
 */
export interface AssistantMessage {
  /** Unique identifier */
  id: string;

  /** Message role */
  role: MessageRole;

  /** Message content */
  content: string;

  /** Timestamp */
  timestamp: Date;

  /** Optional action chips attached to this message */
  actionChips?: ActionChip[];

  /** Whether this is a gating warning message */
  isWarning?: boolean;

  /** Context info when message was sent */
  context?: MessageContext;
}

/**
 * Context information for messages
 */
export interface MessageContext {
  activityId?: string;
  activityName?: string;
  stageId?: string;
  stageName?: string;
  artifactId?: string;
}

/**
 * Current context state for the assistant
 */
export interface AssistantContext {
  /** Current project info */
  projectId: string;
  projectName: string;
  methodologyName: string;

  /** Current stage info */
  currentStageId: string | null;
  currentStageName: string | null;
  stageProgress: number;

  /** Current activity info */
  currentActivityId: string | null;
  currentActivityName: string | null;
  currentActivityStatus: string | null;
  currentActivityCanvasType: CanvasType | null;

  /** Whether the current activity is locked */
  isCurrentActivityLocked: boolean;

  /** Incomplete prerequisites for current activity */
  incompletePrerequisites: PrerequisiteInfo[];
}

/**
 * Information about a prerequisite
 */
export interface PrerequisiteInfo {
  activityId: string;
  activityName: string;
  status: 'not_started' | 'in_progress' | 'complete' | 'blocked' | 'locked';
  stageId: string;
  stageName: string;
}

/**
 * Suggestion trigger type
 */
export type SuggestionTrigger =
  | 'activity_selected'   // User selected an activity
  | 'activity_locked'     // User tried to access locked activity
  | 'activity_completed'  // User completed an activity
  | 'stage_completed'     // User completed a stage
  | 'idle'               // User hasn't acted for a while
  | 'manual';            // User asked for suggestions

/**
 * Category colors for UI
 */
export const CATEGORY_COLORS: Record<ActionCategory, { bg: string; text: string; border: string }> = {
  create: {
    bg: 'var(--color-success-50, #ecfdf5)',
    text: 'var(--color-success-700, #15803d)',
    border: 'var(--color-success-200, #bbf7d0)',
  },
  review: {
    bg: 'var(--color-info-50, #eff6ff)',
    text: 'var(--color-info-700, #1d4ed8)',
    border: 'var(--color-info-200, #bfdbfe)',
  },
  approve: {
    bg: 'var(--color-warning-50, #fffbeb)',
    text: 'var(--color-warning-700, #b45309)',
    border: 'var(--color-warning-200, #fde68a)',
  },
  analyse: {
    bg: 'var(--color-primary-50, #eef2ff)',
    text: 'var(--color-primary-700, #4338ca)',
    border: 'var(--color-primary-200, #c7d2fe)',
  },
  navigate: {
    bg: 'var(--color-neutral-50, #fafafa)',
    text: 'var(--color-neutral-700, #404040)',
    border: 'var(--color-neutral-200, #e5e5e5)',
  },
};

/**
 * Category icons
 */
export const CATEGORY_ICONS: Record<ActionCategory, string> = {
  create: '✨',
  review: '👁',
  approve: '✓',
  analyse: '📊',
  navigate: '→',
};

/**
 * Maps action chip IDs/types to agent IDs for enablement filtering.
 * When an action requires a specific agent, we map it here.
 */
export const ACTION_AGENT_MAPPING: Record<string, string> = {
  // Budget-related actions -> Financial Management Agent
  'generate-budget-from-wbs': 'financial-management',
  'create-budget-manual': 'financial-management',
  'view-budget-status': 'financial-management',

  // Schedule-related actions -> Schedule & Planning Agent
  'generate-schedule-from-wbs': 'schedule-planning',
  'view-schedule-status': 'schedule-planning',

  // Risk-related actions -> Risk & Issue Management Agent
  'open-risk-register': 'agent_015',
  'risk-analysis': 'agent_015',
};

/**
 * Gets the agent ID associated with an action chip, if any.
 */
export function getAgentForAction(chipId: string): string | undefined {
  // Check direct mapping first
  if (ACTION_AGENT_MAPPING[chipId]) {
    return ACTION_AGENT_MAPPING[chipId];
  }

  // Check prefix patterns
  if (chipId.startsWith('budget-') || chipId.includes('-budget')) {
    return 'financial-management';
  }
  if (chipId.startsWith('schedule-') || chipId.includes('-schedule')) {
    return 'schedule-planning';
  }
  if (chipId.startsWith('risk-') || chipId.includes('-risk')) {
    return 'agent_015';
  }

  return undefined;
}
