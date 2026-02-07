/**
 * Connector Store Types
 *
 * Types for connector configuration, categories, and state management.
 */
import type { IconSemantic } from '@/components/icon/iconMap';

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
  | 'compliance'
  | 'iot';

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
 * Certification status for connector compliance evidence
 */
export type CertificationStatus =
  | 'certified'
  | 'pending'
  | 'expired'
  | 'not_certified'
  | 'not_started';

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
  type: 'string' | 'url' | 'number' | 'boolean' | 'select' | 'multiselect';
  required: boolean;
  label: string;
  options?: string[];
}

/**
 * Connector definition (from registry)
 */
export interface ConnectorDefinition {
  connector_id: string;
  name: string;
  description: string;
  category: ConnectorCategory;
  system: string;
  mcp_server_id: string;
  supported_operations: string[];
  mcp_preferred: boolean;
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
  certification_status?: CertificationStatus;
  custom_fields?: Record<string, unknown>;
  mcp_server_url?: string;
  mcp_tool_map?: Record<string, unknown>;
  client_id?: string;
  client_secret?: string;
  scope?: string;
  prefer_mcp?: boolean;
}

/**
 * Evidence document for certification audits
 */
export interface CertificationDocument {
  document_id: string;
  filename: string;
  content_type: string;
  uploaded_at: string;
  uploaded_by?: string | null;
}

/**
 * Certification record for a connector
 */
export interface CertificationRecord {
  connector_id: string;
  tenant_id: string;
  compliance_status: CertificationStatus;
  certification_date?: string | null;
  expires_at?: string | null;
  audit_reference?: string | null;
  notes?: string | null;
  documents: CertificationDocument[];
  updated_at: string;
  updated_by?: string | null;
}

/**
 * Connector configuration update request
 */
export interface ConnectorConfigUpdate {
  instance_url?: string;
  project_key?: string;
  mcp_server_url?: string;
  mcp_server_id?: string;
  client_id?: string;
  client_secret?: string;
  scope?: string;
  mcp_tool_map?: Record<string, unknown>;
  prefer_mcp?: boolean;
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
  icon: IconSemantic;
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
    icon: 'domain.portfolio',
    description: 'Portfolio and Project Management platforms',
  },
  pm: {
    value: 'pm',
    label: 'PM Tools',
    icon: 'provenance.auditLog',
    description: 'Project management and work tracking tools',
  },
  doc_mgmt: {
    value: 'doc_mgmt',
    label: 'Document Management',
    icon: 'artifact.folder',
    description: 'Document storage and collaboration platforms',
  },
  erp: {
    value: 'erp',
    label: 'ERP Systems',
    icon: 'domain.platform',
    description: 'Enterprise resource planning systems',
  },
  hris: {
    value: 'hris',
    label: 'HRIS',
    icon: 'communication.user',
    description: 'Human resource information systems',
  },
  collaboration: {
    value: 'collaboration',
    label: 'Collaboration',
    icon: 'communication.message',
    description: 'Team communication and collaboration tools',
  },
  grc: {
    value: 'grc',
    label: 'GRC',
    icon: 'domain.governance',
    description: 'Governance, Risk, and Compliance platforms',
  },
  compliance: {
    value: 'compliance',
    label: 'Compliance',
    icon: 'domain.governance',
    description: 'Specialised regulatory compliance platforms',
  },
  iot: {
    value: 'iot',
    label: 'IoT Integrations',
    icon: 'connectors.cpuChip',
    description: 'Custom hardware and sensor integrations',
  },
};

/**
 * Filter state for connector gallery
 */
export interface ConnectorFilterState {
  search: string;
  category: ConnectorCategory | 'all';
  statusFilter: ConnectorStatus | 'all';
  certificationFilter: CertificationStatus | 'all';
  enabledOnly: boolean;
}
