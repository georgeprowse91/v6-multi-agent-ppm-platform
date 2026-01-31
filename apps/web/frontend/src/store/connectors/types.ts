/**
 * Connector Store Types
 *
 * Types for connector configuration, categories, and state management.
 */

/**
 * Connector categories for organization
 */
export type ConnectorCategory =
  | 'ppm'
  | 'pm'
  | 'doc_mgmt'
  | 'erp'
  | 'hris'
  | 'collaboration'
  | 'grc'
  | 'compliance';

/**
 * Connector implementation status
 */
export type ConnectorStatus = 'available' | 'coming_soon' | 'beta' | 'production';

/**
 * Sync direction options
 */
export type SyncDirection = 'inbound' | 'outbound' | 'bidirectional';

/**
 * Sync frequency options
 */
export type SyncFrequency =
  | 'realtime'
  | 'hourly'
  | 'every_4_hours'
  | 'daily'
  | 'weekly'
  | 'manual';

/**
 * Connection health status
 */
export type HealthStatus = 'healthy' | 'unhealthy' | 'unknown';

/**
 * Connection test status
 */
export type ConnectionTestStatus =
  | 'connected'
  | 'failed'
  | 'unauthorized'
  | 'timeout'
  | 'invalid_config';

/**
 * Configuration field definition
 */
export interface ConfigField {
  name: string;
  type: 'string' | 'url' | 'number' | 'boolean';
  required: boolean;
  label: string;
}

/**
 * Connector definition (from registry)
 */
export interface ConnectorDefinition {
  connector_id: string;
  name: string;
  description: string;
  category: ConnectorCategory;
  status: ConnectorStatus;
  icon: string;
  supported_sync_directions: SyncDirection[];
  auth_type: string;
  config_fields: ConfigField[];
  env_vars: string[];
}

/**
 * Connector list item (definition + config status)
 */
export interface Connector extends ConnectorDefinition {
  enabled: boolean;
  configured: boolean;
  instance_url: string;
  project_key: string;
  sync_direction: SyncDirection;
  sync_frequency: SyncFrequency;
  health_status: HealthStatus;
  last_sync_at: string | null;
  custom_fields?: Record<string, unknown>;
}

/**
 * Connector configuration update request
 */
export interface ConnectorConfigUpdate {
  instance_url?: string;
  project_key?: string;
  sync_direction?: SyncDirection;
  sync_frequency?: SyncFrequency;
  custom_fields?: Record<string, unknown>;
}

/**
 * Connection test result
 */
export interface ConnectionTestResult {
  status: ConnectionTestStatus;
  message: string;
  details: Record<string, unknown>;
  tested_at: string;
}

/**
 * Category information for display
 */
export interface CategoryInfo {
  value: ConnectorCategory;
  label: string;
  icon: string;
  description: string;
  connector_count: number;
  enabled_connector: string | null;
}

/**
 * Category display metadata
 */
export const CATEGORY_INFO: Record<ConnectorCategory, Omit<CategoryInfo, 'connector_count' | 'enabled_connector'>> = {
  ppm: {
    value: 'ppm',
    label: 'PPM Tools',
    icon: 'chart-bar',
    description: 'Portfolio and Project Management platforms',
  },
  pm: {
    value: 'pm',
    label: 'PM Tools',
    icon: 'clipboard-list',
    description: 'Project management and work tracking tools',
  },
  doc_mgmt: {
    value: 'doc_mgmt',
    label: 'Document Management',
    icon: 'folder',
    description: 'Document storage and collaboration platforms',
  },
  erp: {
    value: 'erp',
    label: 'ERP Systems',
    icon: 'building-office',
    description: 'Enterprise resource planning systems',
  },
  hris: {
    value: 'hris',
    label: 'HRIS',
    icon: 'users',
    description: 'Human resource information systems',
  },
  collaboration: {
    value: 'collaboration',
    label: 'Collaboration',
    icon: 'chat-bubble-left-right',
    description: 'Team communication and collaboration tools',
  },
  grc: {
    value: 'grc',
    label: 'GRC',
    icon: 'shield-check',
    description: 'Governance, Risk, and Compliance platforms',
  },
  compliance: {
    value: 'compliance',
    label: 'Compliance',
    icon: 'shield-check',
    description: 'Specialised regulatory compliance platforms',
  },
};

/**
 * Filter state for connector gallery
 */
export interface ConnectorFilterState {
  search: string;
  category: ConnectorCategory | 'all';
  statusFilter: ConnectorStatus | 'all';
  enabledOnly: boolean;
}
