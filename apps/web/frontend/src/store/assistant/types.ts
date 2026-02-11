/**
 * Assistant Types - Data model for the AI assistant panel
 *
 * Supports:
 * - Chat messages with different roles
 * - Next Best Action chips with categories
 * - Context-aware suggestions based on methodology state
 */

import type { CanvasType } from '@ppm/canvas-engine';
import type { IconSemantic } from '@/components/icon/iconMap';

/**
 * Message roles in the assistant chat
 */
export type MessageRole = 'user' | 'assistant' | 'system';

export type ScopeResearchStatus = 'pending' | 'accepted' | 'rejected';

export interface ScopeResearchItem {
  id: string;
  text: string;
  status: ScopeResearchStatus;
}

export interface ScopeResearchMessageData {
  objective?: string;
  scope?: ScopeResearchItem[];
  requirements?: ScopeResearchItem[];
  wbs?: ScopeResearchItem[];
  sources?: string[];
  notice?: string;
  usedExternalResearch?: boolean;
}

export type ConversationalChangeStatus = 'add' | 'update' | 'remove';

export interface ConversationalChange {
  id: string;
  label: string;
  before?: string | number | null;
  after?: string | number | null;
  status?: ConversationalChangeStatus;
}

export interface ConversationalCommandMessageData {
  title: string;
  summary?: string;
  changes: ConversationalChange[];
  applyLabel?: string;
}

export type AssistantMessageType =
  | 'text'
  | 'scope_research'
  | 'conversational_command'
  | 'typing'
  | 'welcome';

/**
 * Assistant AI state model for UX standards
 */
export type AIState =
  | 'idle'
  | 'thinking'
  | 'streaming'
  | 'tool_use'
  | 'needs_user_input'
  | 'completed'
  | 'uncertain'
  | 'error'
  | 'refusal';

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
  | 'scope_research'     // Trigger external scope research
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

  /** Icon semantic */
  icon?: IconSemantic;

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
  | ScopeResearchPayload
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

export interface ScopeResearchPayload {
  type: 'scope_research';
  objective?: string;
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

  /** Message rendering type */
  messageType?: AssistantMessageType;

  /** Optional structured message payload */
  data?: Record<string, unknown>;

  /** Timestamp */
  timestamp: Date;

  /** Optional action chips attached to this message */
  actionChips?: ActionChip[];

  /** Whether this is a gating warning message */
  isWarning?: boolean;

  /** Assistant state when message was created */
  aiState?: AIState;

  /** Optional list of sources or citations */
  sources?: string[];

  /** Provenance metadata */
  provenance?: {
    generated: boolean;
    modelOrTool?: string;
    showModelOrTool?: boolean;
  };

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
    bg: 'var(--color-state-success-bg)',
    text: 'var(--color-state-success-fg)',
    border: 'var(--color-state-success-fg)',
  },
  review: {
    bg: 'var(--color-state-info-bg)',
    text: 'var(--color-state-info-fg)',
    border: 'var(--color-state-info-fg)',
  },
  approve: {
    bg: 'var(--color-state-warning-bg)',
    text: 'var(--color-state-warning-fg)',
    border: 'var(--color-state-warning-fg)',
  },
  analyse: {
    bg: 'var(--color-brand-orange-100)',
    text: 'var(--color-brand-orange-500)',
    border: 'var(--color-brand-orange-500)',
  },
  navigate: {
    bg: 'var(--color-surface-subtle)',
    text: 'var(--color-text-primary)',
    border: 'var(--color-border-default)',
  },
};

/**
 * Category icons
 */
export const CATEGORY_ICONS: Record<ActionCategory, IconSemantic> = {
  create: 'ai.suggestion',
  review: 'actions.preview',
  approve: 'actions.confirmApply',
  analyse: 'ai.explainability',
  navigate: 'navigation.next',
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
/**
 * API response type for suggestion endpoint
 */
export interface SuggestionApiResponse {
  id: string;
  label: string;
  category: ActionCategory;
  priority: ActionPriority;
  icon?: IconSemantic;
  action_type: ActionType;
  payload: ActionPayload;
  enabled?: boolean;
  description?: string;
}

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
