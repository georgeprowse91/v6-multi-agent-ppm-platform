/**
 * ConnectorGallery - Connector configuration gallery page
 *
 * Features:
 * - List connectors by category
 * - Search and filter functionality
 * - Enable/disable connectors with mutual exclusivity
 * - Open configuration modal for detailed settings
 * - Test connection functionality
 */

import { useEffect, useMemo, useState } from 'react';
import {
  useConnectorStore,
  CATEGORY_INFO,
  type CertificationRecord,
  type Connector,
  type ConnectorCategory,
} from '@/store/connectors';
import { useAppStore } from '@/store';
import { canManageConfig } from '@/auth/permissions';
import { SyncStatusPanel } from './SyncStatusPanel';
import styles from './ConnectorGallery.module.css';

export function ConnectorGallery() {
  const {
    connectors,
    connectorsLoading,
    connectorsError,
    certifications,
    certificationsLoading,
    fetchCertifications,
    filter,
    fetchConnectors,
    fetchCategories,
    setFilter,
    resetFilter,
    getFilteredConnectors,
    enableConnector,
    disableConnector,
    openConnectorModal,
    isModalOpen,
    selectedConnector,
    closeConnectorModal,
    updateConnectorConfig,
    testConnection,
    testingConnection,
    testResult,
    clearTestResult,
    updateCertification,
    uploadCertificationDocument,
  } = useConnectorStore();
  const { session } = useAppStore();
  const canManage = canManageConfig(session.user?.roles);
  const [certModalOpen, setCertModalOpen] = useState(false);
  const [certModalConnector, setCertModalConnector] = useState<Connector | null>(null);
  const statusOptions: { value: Connector['status'] | 'all'; label: string }[] = [
    { value: 'all', label: 'All Status' },
    { value: 'production', label: 'Production' },
    { value: 'available', label: 'Available' },
    { value: 'beta', label: 'Beta' },
    { value: 'coming_soon', label: 'Coming Soon' },
  ];

  // Initialize store
  useEffect(() => {
    fetchConnectors();
    fetchCategories();
    fetchCertifications();
  }, [fetchConnectors, fetchCategories, fetchCertifications]);

  // Get filtered connectors
  const filteredConnectors = useMemo(() => getFilteredConnectors(), [connectors, filter, getFilteredConnectors]);

  // Group connectors by category
  const connectorsByCategory = useMemo(() => {
    const grouped: Record<ConnectorCategory, Connector[]> = {
      ppm: [],
      pm: [],
      doc_mgmt: [],
      erp: [],
      hris: [],
      collaboration: [],
      grc: [],
      compliance: [],
      iot: [],
    };
    filteredConnectors.forEach((connector) => {
      if (grouped[connector.category]) {
        grouped[connector.category].push(connector);
      }
    });
    return grouped;
  }, [filteredConnectors]);

  // Get categories that have connectors
  const activeCategories = useMemo(() => {
    return (Object.keys(connectorsByCategory) as ConnectorCategory[]).filter(
      (cat) => connectorsByCategory[cat].length > 0
    );
  }, [connectorsByCategory]);

  const handleToggleEnabled = async (connector: Connector) => {
    if (!canManage) return;
    if (!isConnectorToggleable(connector.status)) return;
    if (connector.enabled) {
      await disableConnector(connector.connector_id);
    } else {
      await enableConnector(connector.connector_id);
    }
  };

  const handleOpenConfig = (connector: Connector) => {
    if (!canManage) return;
    openConnectorModal(connector);
  };

  const handleOpenCertification = (connector: Connector) => {
    setCertModalConnector(connector);
    setCertModalOpen(true);
  };

  const handleCloseCertification = () => {
    setCertModalConnector(null);
    setCertModalOpen(false);
  };

  if (connectorsLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading connectors...</div>
      </div>
    );
  }

  if (connectorsError && connectors.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <p>Error loading connectors: {connectorsError}</p>
          <button onClick={fetchConnectors}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container} data-tour="connector-gallery">
      <SyncStatusPanel />
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>Connector Gallery</h1>
          <p className={styles.subtitle}>
            Configure integrations with external systems. Enable connectors to sync data with your PPM platform.
          </p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.connectorStats}>
            {connectors.filter((c) => c.enabled).length} of {connectors.length} connectors enabled
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchBox}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search connectors..."
            value={filter.search}
            onChange={(e) => setFilter({ search: e.target.value })}
          />
          {filter.search && (
            <button
              className={styles.clearSearch}
              onClick={() => setFilter({ search: '' })}
              title="Clear search"
            >
              x
            </button>
          )}
        </div>

        <select
          className={styles.categorySelect}
          value={filter.category}
          onChange={(e) => setFilter({ category: e.target.value as ConnectorCategory | 'all' })}
        >
          <option value="all">All Categories</option>
          {Object.values(CATEGORY_INFO).map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>

        <select
          className={styles.statusSelect}
          value={filter.statusFilter}
          onChange={(e) =>
            setFilter({
              statusFilter: e.target.value as Connector['status'] | 'all',
            })
          }
        >
          {statusOptions.map((status) => (
            <option key={status.value} value={status.value}>
              {status.label}
            </option>
          ))}
        </select>

        <label className={styles.enabledFilter}>
          <input
            type="checkbox"
            checked={filter.enabledOnly}
            onChange={(e) => setFilter({ enabledOnly: e.target.checked })}
          />
          <span>Enabled only</span>
        </label>

        <button className={styles.resetButton} onClick={resetFilter}>
          Reset Filters
        </button>
      </div>

      {/* Stats */}
      <div className={styles.stats}>
        <span>
          Showing {filteredConnectors.length} of {connectors.length} connectors
        </span>
      </div>

      {/* Connector List by Category */}
      <div className={styles.connectorList}>
        {activeCategories.length === 0 ? (
          <div className={styles.empty}>
            <p>No connectors match your filters.</p>
          </div>
        ) : (
          activeCategories.map((category) => (
            <CategorySection
              key={category}
              category={category}
              connectors={connectorsByCategory[category]}
              onToggleEnabled={handleToggleEnabled}
              onOpenConfig={handleOpenConfig}
              onOpenCertification={handleOpenCertification}
              canManage={canManage}
              certifications={certifications}
            />
          ))
        )}
      </div>

      {/* Config Modal */}
      {isModalOpen && selectedConnector && (
        <ConnectorConfigModal
          connector={selectedConnector}
          onClose={closeConnectorModal}
          onSave={updateConnectorConfig}
          onTestConnection={testConnection}
          testingConnection={testingConnection}
          testResult={testResult}
          clearTestResult={clearTestResult}
        />
      )}

      {certModalOpen && certModalConnector && (
        <CertificationModal
          connector={certModalConnector}
          certification={certifications[certModalConnector.connector_id]}
          canManage={canManage}
          loading={certificationsLoading}
          onClose={handleCloseCertification}
          onSave={updateCertification}
          onUploadDocument={uploadCertificationDocument}
          updatedBy={session.user?.name ?? session.user?.id ?? undefined}
        />
      )}
    </div>
  );
}

/**
 * Category section component
 */
interface CategorySectionProps {
  category: ConnectorCategory;
  connectors: Connector[];
  onToggleEnabled: (connector: Connector) => void;
  onOpenConfig: (connector: Connector) => void;
  onOpenCertification: (connector: Connector) => void;
  canManage: boolean;
  certifications: Record<string, CertificationRecord>;
}

function CategorySection({
  category,
  connectors,
  onToggleEnabled,
  onOpenConfig,
  onOpenCertification,
  canManage,
  certifications,
}: CategorySectionProps) {
  const info = CATEGORY_INFO[category];
  const enabledConnector = connectors.find((c) => c.enabled);

  return (
    <section className={styles.categorySection}>
      <div className={styles.categoryHeader}>
        <div className={styles.categoryInfo}>
          <h2 className={styles.categoryTitle}>{info.label}</h2>
          <p className={styles.categoryDescription}>{info.description}</p>
        </div>
        <div className={styles.categoryMeta}>
          <span className={styles.categoryCount}>{connectors.length} connectors</span>
          {enabledConnector && (
            <span className={styles.enabledBadge}>
              {enabledConnector.name} enabled
            </span>
          )}
        </div>
      </div>

      <div className={styles.connectorGrid}>
        {connectors.map((connector) => (
          <ConnectorCard
            key={connector.connector_id}
            connector={connector}
            onToggleEnabled={() => onToggleEnabled(connector)}
            onOpenConfig={() => onOpenConfig(connector)}
            onOpenCertification={() => onOpenCertification(connector)}
            canManage={canManage}
            certification={certifications[connector.connector_id]}
          />
        ))}
      </div>
    </section>
  );
}

/**
 * Connector card component
 */
interface ConnectorCardProps {
  connector: Connector;
  onToggleEnabled: () => void;
  onOpenConfig: () => void;
  onOpenCertification: () => void;
  canManage: boolean;
  certification?: CertificationRecord;
}

function ConnectorCard({
  connector,
  onToggleEnabled,
  onOpenConfig,
  onOpenCertification,
  canManage,
  certification,
}: ConnectorCardProps) {
  const statusLabel = STATUS_LABELS[connector.status];
  const statusClassName = STATUS_BADGE_CLASSES[connector.status];
  const isToggleable = isConnectorToggleable(connector.status);
  const canToggle = canManage && isToggleable;
  const certStatus = certification?.compliance_status ?? 'not_tracked';
  const certLabel = CERTIFICATION_LABELS[certStatus];
  const certBadgeClass = CERTIFICATION_BADGE_CLASSES[certStatus];

  return (
    <div
      className={`${styles.connectorCard} ${
        !isToggleable ? styles.unavailable : ''
      } ${connector.enabled ? styles.enabled : ''}`}
    >
      <div className={styles.cardHeader}>
        <div className={styles.connectorIcon}>
          <ConnectorIcon name={connector.icon} />
        </div>
        <div className={styles.connectorTitle}>
          <h3 className={styles.connectorName}>{connector.name}</h3>
          <span className={`${styles.statusBadge} ${statusClassName}`}>{statusLabel}</span>
        </div>
        <label
          className={styles.toggleSwitch}
          title={
            !isToggleable
              ? 'Not available yet'
              : canManage
              ? 'Toggle enabled'
              : 'Read-only'
          }
        >
          <input
            type="checkbox"
            checked={connector.enabled}
            onChange={onToggleEnabled}
            disabled={!canToggle}
            aria-label={`Toggle ${connector.name}`}
          />
          <span className={styles.toggleSlider}></span>
        </label>
      </div>

      <p className={styles.connectorDescription}>{connector.description}</p>

      <div className={styles.connectorMeta}>
        <span className={styles.syncDirection}>
          {connector.sync_direction === 'inbound' && 'Read'}
          {connector.sync_direction === 'outbound' && 'Write'}
          {connector.sync_direction === 'bidirectional' && 'Read/Write'}
        </span>
        {connector.configured && (
          <span className={`${styles.healthStatus} ${styles[connector.health_status]}`}>
            {connector.health_status === 'healthy' && 'Connected'}
            {connector.health_status === 'unhealthy' && 'Disconnected'}
            {connector.health_status === 'unknown' && 'Not tested'}
          </span>
        )}
        <span className={`${styles.certificationBadge} ${certBadgeClass}`}>
          {certLabel}
        </span>
      </div>

      <div className={styles.cardActions}>
        <button
          className={styles.configButton}
          onClick={onOpenConfig}
          disabled={!canToggle}
          title={
            !isToggleable
              ? 'Not available yet'
              : canManage
              ? 'Configure connector'
              : 'Read-only'
          }
        >
          Configure
        </button>
        <button
          className={styles.certButton}
          onClick={onOpenCertification}
          data-tour="certification-evidence"
        >
          {canManage ? 'Manage Evidence' : 'View Evidence'}
        </button>
      </div>
    </div>
  );
}

/**
 * Simple icon component for connectors
 */
function ConnectorIcon({ name }: { name: string }) {
  // Simple SVG icons for each connector
  const icons: Record<string, JSX.Element> = {
    jira: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.78v1.7c0 2.4 1.94 4.34 4.34 4.35V2.84a.84.84 0 00-.84-.84H11.53zM6.77 6.8a4.362 4.362 0 004.34 4.38h1.8v1.7c0 2.4 1.93 4.34 4.34 4.35V7.66a.84.84 0 00-.85-.85H6.77zM2 11.6c0 2.4 1.95 4.34 4.35 4.35h1.78v1.7c.01 2.39 1.95 4.34 4.35 4.35v-9.57a.84.84 0 00-.85-.84H2z"/>
      </svg>
    ),
    azure: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M13.05 4.24L6.56 18.05h2.22l1.47-3.26h5.5l.47 3.26h2.22L13.05 4.24zm.91 8.55H10.7l2.1-5.01 1.16 5.01z"/>
      </svg>
    ),
    slack: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M6 15a2 2 0 01-2 2 2 2 0 01-2-2 2 2 0 012-2h2v2zm1 0a2 2 0 012-2 2 2 0 012 2v5a2 2 0 01-2 2 2 2 0 01-2-2v-5zm2-8a2 2 0 01-2-2 2 2 0 012-2 2 2 0 012 2v2H9zm0 1a2 2 0 012 2 2 2 0 01-2 2H4a2 2 0 01-2-2 2 2 0 012-2h5zm8 2a2 2 0 012-2 2 2 0 012 2 2 2 0 01-2 2h-2v-2zm-1 0a2 2 0 01-2 2 2 2 0 01-2-2V5a2 2 0 012-2 2 2 0 012 2v5zm-2 8a2 2 0 012 2 2 2 0 01-2 2 2 2 0 01-2-2v-2h2zm0-1a2 2 0 01-2-2 2 2 0 012-2h5a2 2 0 012 2 2 2 0 01-2 2h-5z"/>
      </svg>
    ),
    teams: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M19.19 8.77a2.49 2.49 0 01-.69-.28 2.5 2.5 0 10-3.49 2.37v4.75a3.39 3.39 0 01-3.39 3.39H6.77a3.4 3.4 0 01-3.4-3.4V9.1a3.4 3.4 0 013.4-3.4h5.85a3.39 3.39 0 013.06 1.94 2.5 2.5 0 003.51 1.13zM8 12.5a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"/>
      </svg>
    ),
    sharepoint: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M12 4a8 8 0 100 16 8 8 0 000-16zm0 2a6 6 0 110 12 6 6 0 010-12zm-1 3v6h2v-6h-2zm-2 2v2h6v-2H9z"/>
      </svg>
    ),
    'cpu-chip': (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M9 3h6v2h2v2h2v6h-2v2h-2v2H9v-2H7v-2H5V7h2V5h2V3zm0 4v8h6V7H9z"/>
      </svg>
    ),
    default: (
      <svg viewBox="0 0 24 24" fill="currentColor" className={styles.iconSvg}>
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
      </svg>
    ),
  };

  return icons[name] || icons.default;
}

/**
 * Connector configuration modal component
 */
interface ConnectorConfigModalProps {
  connector: Connector;
  onClose: () => void;
  onSave: (connectorId: string, config: { instance_url?: string; project_key?: string; sync_direction?: string; sync_frequency?: string; custom_fields?: Record<string, unknown> }) => Promise<void>;
  onTestConnection: (connectorId: string, instanceUrl?: string, projectKey?: string) => Promise<{ status: string; message: string }>;
  testingConnection: boolean;
  testResult: { status: string; message: string; details: Record<string, unknown> } | null;
  clearTestResult: () => void;
}

function ConnectorConfigModal({
  connector,
  onClose,
  onSave,
  onTestConnection,
  testingConnection,
  testResult,
  clearTestResult,
}: ConnectorConfigModalProps) {
  const customFields = connector.custom_fields ?? {};
  const isIoT = connector.category === 'iot';
  const [instanceUrl, setInstanceUrl] = useState(connector.instance_url || '');
  const [projectKey, setProjectKey] = useState(connector.project_key || '');
  const [deviceEndpoint, setDeviceEndpoint] = useState(
    (customFields.device_endpoint as string) || connector.instance_url || ''
  );
  const [authToken, setAuthToken] = useState((customFields.auth_token as string) || '');
  const [sensorTypes, setSensorTypes] = useState((customFields.sensor_types as string) || '');
  const [syncDirection, setSyncDirection] = useState(connector.sync_direction);
  const [syncFrequency, setSyncFrequency] = useState(connector.sync_frequency);
  const [saving, setSaving] = useState(false);
  const connectionTarget = isIoT ? deviceEndpoint : instanceUrl;

  const handleSave = async () => {
    setSaving(true);
    try {
      const effectiveInstanceUrl = isIoT ? deviceEndpoint : instanceUrl;
      await onSave(connector.connector_id, {
        instance_url: effectiveInstanceUrl,
        project_key: projectKey,
        sync_direction: syncDirection,
        sync_frequency: syncFrequency,
        custom_fields: isIoT
          ? {
              device_endpoint: deviceEndpoint,
              auth_token: authToken,
              sensor_types: sensorTypes,
            }
          : undefined,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    clearTestResult();
    const effectiveInstanceUrl = isIoT ? deviceEndpoint : instanceUrl;
    await onTestConnection(connector.connector_id, effectiveInstanceUrl, projectKey);
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div className={styles.modalTitleSection}>
            <ConnectorIcon name={connector.icon} />
            <h2 className={styles.modalTitle}>{connector.name} Configuration</h2>
          </div>
          <button className={styles.modalClose} onClick={onClose}>
            x
          </button>
        </div>

        <div className={styles.modalBody}>
          <p className={styles.modalDescription}>{connector.description}</p>

          <div className={styles.configSection}>
            <h3 className={styles.sectionTitle}>Connection Settings</h3>

            <div className={styles.formField}>
              <label className={styles.fieldLabel}>
                {isIoT ? 'Device Endpoint' : 'Instance URL'}
              </label>
              <input
                type="url"
                className={styles.fieldInput}
                placeholder={isIoT ? 'https://device-gateway.example.com' : 'https://your-instance.example.com'}
                value={isIoT ? deviceEndpoint : instanceUrl}
                onChange={(e) =>
                  isIoT ? setDeviceEndpoint(e.target.value) : setInstanceUrl(e.target.value)
                }
              />
              <span className={styles.fieldHint}>
                {isIoT
                  ? 'The REST endpoint for your device gateway or IoT hub'
                  : `The base URL of your ${connector.name} instance`}
              </span>
            </div>

            {isIoT && (
              <>
                <div className={styles.formField}>
                  <label className={styles.fieldLabel}>Authentication Token</label>
                  <input
                    type="password"
                    className={styles.fieldInput}
                    placeholder="e.g., bearer token"
                    value={authToken}
                    onChange={(e) => setAuthToken(e.target.value)}
                  />
                  <span className={styles.fieldHint}>
                    Token or API key used to authenticate with the IoT device gateway
                  </span>
                </div>
                <div className={styles.formField}>
                  <label className={styles.fieldLabel}>Supported Sensor Types</label>
                  <input
                    type="text"
                    className={styles.fieldInput}
                    placeholder="temperature, humidity, vibration"
                    value={sensorTypes}
                    onChange={(e) => setSensorTypes(e.target.value)}
                  />
                  <span className={styles.fieldHint}>
                    Comma-separated sensor types for ingestion routing
                  </span>
                </div>
              </>
            )}

            {connector.connector_id === 'jira' && (
              <div className={styles.formField}>
                <label className={styles.fieldLabel}>Project Key (Optional)</label>
                <input
                  type="text"
                  className={styles.fieldInput}
                  placeholder="e.g., PROJ"
                  value={projectKey}
                  onChange={(e) => setProjectKey(e.target.value)}
                />
                <span className={styles.fieldHint}>
                  Filter issues to a specific project
                </span>
              </div>
            )}

            <div className={styles.envVarNotice}>
              <strong>Note:</strong> API credentials must be configured via environment variables:
              <ul>
                {connector.env_vars.map((envVar) => (
                  <li key={envVar}><code>{envVar}</code></li>
                ))}
              </ul>
            </div>
          </div>

          <div className={styles.configSection}>
            <h3 className={styles.sectionTitle}>Sync Settings</h3>

            <div className={styles.formField}>
              <label className={styles.fieldLabel}>Sync Direction</label>
              <select
                className={styles.fieldSelect}
                value={syncDirection}
                onChange={(e) => setSyncDirection(e.target.value as typeof syncDirection)}
              >
                {connector.supported_sync_directions.includes('inbound') && (
                  <option value="inbound">Inbound (Read from {connector.name})</option>
                )}
                {connector.supported_sync_directions.includes('outbound') && (
                  <option value="outbound">Outbound (Write to {connector.name})</option>
                )}
                {connector.supported_sync_directions.includes('bidirectional') && (
                  <option value="bidirectional">Bidirectional (Read & Write)</option>
                )}
              </select>
            </div>

            <div className={styles.formField}>
              <label className={styles.fieldLabel}>Sync Frequency</label>
              <select
                className={styles.fieldSelect}
                value={syncFrequency}
                onChange={(e) => setSyncFrequency(e.target.value as typeof syncFrequency)}
              >
                <option value="realtime">Real-time (via webhooks)</option>
                <option value="hourly">Hourly</option>
                <option value="every_4_hours">Every 4 hours</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="manual">Manual only</option>
              </select>
            </div>
          </div>

          {/* Test Connection Section */}
          <div className={styles.testConnectionSection}>
            <button
              className={styles.testButton}
              onClick={handleTestConnection}
              disabled={testingConnection || !connectionTarget}
            >
              {testingConnection ? 'Testing...' : 'Test Connection'}
            </button>

            {testResult && (
              <div className={`${styles.testResult} ${styles[testResult.status]}`}>
                <span className={styles.testResultIcon}>
                  {testResult.status === 'connected' ? '✓' : '✗'}
                </span>
                <div className={styles.testResultContent}>
                  <strong>{testResult.status === 'connected' ? 'Connected' : 'Failed'}</strong>
                  <p>{testResult.message}</p>
                  {testResult.details && testResult.status === 'connected' && (
                    <ul className={styles.testDetails}>
                      {testResult.details.user && <li>User: {String(testResult.details.user)}</li>}
                      {testResult.details.email && <li>Email: {String(testResult.details.email)}</li>}
                      {testResult.details.project && <li>Project: {String(testResult.details.project)}</li>}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.modalFooter}>
          <button className={styles.cancelButton} onClick={onClose}>
            Cancel
          </button>
          <button
            className={styles.saveButton}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}

interface CertificationModalProps {
  connector: Connector;
  certification?: CertificationRecord;
  canManage: boolean;
  loading: boolean;
  updatedBy?: string;
  onClose: () => void;
  onSave: (
    connectorId: string,
    payload: Partial<{
      compliance_status: CertificationRecord['compliance_status'];
      certification_date: string | null;
      expires_at: string | null;
      audit_reference: string | null;
      notes: string | null;
      updated_by?: string;
    }>
  ) => Promise<CertificationRecord | null>;
  onUploadDocument: (
    connectorId: string,
    file: File,
    uploadedBy?: string
  ) => Promise<CertificationRecord | null>;
}

function CertificationModal({
  connector,
  certification,
  canManage,
  loading,
  updatedBy,
  onClose,
  onSave,
  onUploadDocument,
}: CertificationModalProps) {
  const [status, setStatus] = useState<CertificationRecord['compliance_status']>(
    certification?.compliance_status ?? 'pending'
  );
  const [certificationDate, setCertificationDate] = useState(certification?.certification_date ?? '');
  const [expiresAt, setExpiresAt] = useState(certification?.expires_at ?? '');
  const [auditReference, setAuditReference] = useState(certification?.audit_reference ?? '');
  const [notes, setNotes] = useState(certification?.notes ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    setStatus(certification?.compliance_status ?? 'pending');
    setCertificationDate(certification?.certification_date ?? '');
    setExpiresAt(certification?.expires_at ?? '');
    setAuditReference(certification?.audit_reference ?? '');
    setNotes(certification?.notes ?? '');
  }, [certification]);

  const handleSave = async () => {
    setSaving(true);
    await onSave(connector.connector_id, {
      compliance_status: status,
      certification_date: certificationDate || null,
      expires_at: expiresAt || null,
      audit_reference: auditReference || null,
      notes: notes || null,
      updated_by: updatedBy,
    });
    setSaving(false);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    await onUploadDocument(connector.connector_id, file, updatedBy);
    setFile(null);
    setUploading(false);
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div className={styles.modalTitleSection}>
            <ConnectorIcon name={connector.icon} />
            <h2 className={styles.modalTitle}>{connector.name} Certification Evidence</h2>
          </div>
          <button className={styles.modalClose} onClick={onClose}>
            x
          </button>
        </div>
        <div className={styles.modalBody}>
          <p className={styles.modalDescription}>
            Track certification status, audit references, and evidence documents for this connector.
          </p>

          <div className={styles.certGrid}>
            <label className={styles.field}>
              <span>Status</span>
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as CertificationRecord['compliance_status'])
                }
                disabled={!canManage || loading}
              >
                <option value="certified">Certified</option>
                <option value="pending">Pending review</option>
                <option value="expired">Expired</option>
                <option value="not_certified">Not certified</option>
              </select>
            </label>

            <label className={styles.field}>
              <span>Certification date</span>
              <input
                type="date"
                value={certificationDate ?? ''}
                onChange={(event) => setCertificationDate(event.target.value)}
                disabled={!canManage || loading}
              />
            </label>

            <label className={styles.field}>
              <span>Expiration date</span>
              <input
                type="date"
                value={expiresAt ?? ''}
                onChange={(event) => setExpiresAt(event.target.value)}
                disabled={!canManage || loading}
              />
            </label>
          </div>

          <label className={styles.field}>
            <span>Audit reference</span>
            <input
              type="text"
              value={auditReference ?? ''}
              onChange={(event) => setAuditReference(event.target.value)}
              disabled={!canManage || loading}
              placeholder="SOC 2 report ID, ISO certificate number, etc."
            />
          </label>

          <label className={styles.field}>
            <span>Notes</span>
            <textarea
              value={notes ?? ''}
              onChange={(event) => setNotes(event.target.value)}
              disabled={!canManage || loading}
              rows={3}
            />
          </label>

          <div className={styles.certDocuments}>
            <h3>Evidence documents</h3>
            {certification?.documents?.length ? (
              <ul className={styles.documentList}>
                {certification.documents.map((doc) => (
                  <li key={doc.document_id}>
                    <div className={styles.documentName}>{doc.filename}</div>
                    <div className={styles.documentMeta}>
                      <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                      {doc.uploaded_by && <span>Uploaded by {doc.uploaded_by}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.emptyDocuments}>No evidence uploaded yet.</p>
            )}

            {canManage && (
              <div className={styles.uploadRow}>
                <input
                  type="file"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <button
                  className={styles.uploadButton}
                  onClick={handleUpload}
                  disabled={!file || uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload Evidence'}
                </button>
              </div>
            )}
          </div>
        </div>

        <div className={styles.modalFooter}>
          <button className={styles.secondaryButton} onClick={onClose}>
            Close
          </button>
          {canManage && (
            <button className={styles.primaryButton} onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save Updates'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConnectorGallery;

const STATUS_LABELS: Record<Connector['status'], string> = {
  available: 'Available',
  coming_soon: 'Coming Soon',
  beta: 'Beta',
  production: 'Production',
};

const STATUS_BADGE_CLASSES: Record<Connector['status'], string> = {
  available: styles.statusBadgeAvailable,
  coming_soon: styles.statusBadgeComingSoon,
  beta: styles.statusBadgeBeta,
  production: styles.statusBadgeProduction,
};

const CERTIFICATION_LABELS: Record<
  CertificationRecord['compliance_status'] | 'not_tracked',
  string
> = {
  certified: 'Certified',
  pending: 'Pending',
  expired: 'Expired',
  not_certified: 'Not certified',
  not_tracked: 'Not tracked',
};

const CERTIFICATION_BADGE_CLASSES: Record<
  CertificationRecord['compliance_status'] | 'not_tracked',
  string
> = {
  certified: styles.certBadgeCertified,
  pending: styles.certBadgePending,
  expired: styles.certBadgeExpired,
  not_certified: styles.certBadgeNotCertified,
  not_tracked: styles.certBadgeNotTracked,
};

const isConnectorToggleable = (status: Connector['status']) =>
  status === 'available' || status === 'production';
