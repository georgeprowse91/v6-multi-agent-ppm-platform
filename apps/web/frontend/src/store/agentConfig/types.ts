/**
 * Agent Configuration Types
 *
 * Types for agent gallery configuration, enablement, and parameters.
 */

/**
 * Agent categories for grouping
 */
export type AgentCategory =
  | 'core'
  | 'portfolio'
  | 'delivery'
  | 'operations'
  | 'platform'
  | 'governance';

/**
 * User roles for permission checks
 */
export type UserRole = 'admin' | 'pm' | 'member';

/**
 * Parameter types for agent configuration
 */
export type ParameterType = 'string' | 'number' | 'boolean' | 'select' | 'multiselect';

/**
 * A configurable parameter for an agent
 */
export interface AgentParameter {
  name: string;
  display_name: string;
  description: string;
  param_type: ParameterType;
  default_value: unknown;
  current_value?: unknown;
  options?: string[];
  min_value?: number;
  max_value?: number;
  required: boolean;
}

/**
 * Agent configuration
 */
export interface AgentConfig {
  catalog_id: string;
  agent_id: string;
  display_name: string;
  description: string;
  category: AgentCategory;
  enabled: boolean;
  parameters: AgentParameter[];
  capabilities: string[];
  updated_at?: string;
  updated_by?: string;
}

/**
 * Project-specific agent configuration
 */
export interface ProjectAgentConfig {
  project_id: string;
  agent_id: string;
  enabled: boolean;
  parameter_overrides: Record<string, unknown>;
  updated_at?: string;
  updated_by?: string;
}

/**
 * Development user profile for RBAC
 */
export interface DevUser {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  tenant_id: string;
}

/**
 * Category metadata for display
 */
export interface CategoryInfo {
  value: AgentCategory;
  label: string;
  icon: string;
  description: string;
}

/**
 * Category display information
 */
export const CATEGORY_INFO: Record<AgentCategory, CategoryInfo> = {
  core: {
    value: 'core',
    label: 'Core',
    icon: '⚙️',
    description: 'Core system agents for routing and orchestration',
  },
  portfolio: {
    value: 'portfolio',
    label: 'Portfolio',
    icon: '📊',
    description: 'Portfolio management and investment agents',
  },
  delivery: {
    value: 'delivery',
    label: 'Delivery',
    icon: '🚀',
    description: 'Project and program delivery agents',
  },
  operations: {
    value: 'operations',
    label: 'Operations',
    icon: '🔧',
    description: 'Operational management and support agents',
  },
  platform: {
    value: 'platform',
    label: 'Platform',
    icon: '🏗️',
    description: 'Platform services and infrastructure agents',
  },
  governance: {
    value: 'governance',
    label: 'Governance',
    icon: '🛡️',
    description: 'Governance, compliance, and approval agents',
  },
};

/**
 * Sorting options for agent list
 */
export type SortOption = 'name' | 'category' | 'status';

/**
 * Filter state for agent gallery
 */
export interface AgentFilterState {
  search: string;
  category: AgentCategory | 'all';
  enabledOnly: boolean;
  sortBy: SortOption;
}
