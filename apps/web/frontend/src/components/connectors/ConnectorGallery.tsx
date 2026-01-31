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
import { useConnectorStore, CATEGORY_INFO, type Connector, type ConnectorCategory } from '@/store/connectors';
import { useAppStore } from '@/store';
import { canManageConfig } from '@/auth/permissions';
import { SyncStatusPanel } from './SyncStatusPanel';
import styles from './ConnectorGallery.module.css';

export function ConnectorGallery() {
  const {
    connectors,
    connectorsLoading,
    connectorsError,
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
  } = useConnectorStore();
  const { session } = useAppStore();
  const canManage = canManageConfig(session.user?.roles);
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
  }, [fetchConnectors, fetchCategories]);

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
    <div className={styles.container}>
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
              canManage={canManage}
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
  canManage: boolean;
}

function CategorySection({
  category,
  connectors,
  onToggleEnabled,
  onOpenConfig,
  canManage,
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
            canManage={canManage}
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
  canManage: boolean;
}

function ConnectorCard({
  connector,
  onToggleEnabled,
  onOpenConfig,
  canManage,
}: ConnectorCardProps) {
  const statusLabel = STATUS_LABELS[connector.status];
  const statusClassName = STATUS_BADGE_CLASSES[connector.status];
  const isToggleable = isConnectorToggleable(connector.status);
  const canToggle = canManage && isToggleable;

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
  onSave: (connectorId: string, config: { instance_url?: string; project_key?: string; sync_direction?: string; sync_frequency?: string }) => Promise<void>;
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
  const [instanceUrl, setInstanceUrl] = useState(connector.instance_url || '');
  const [projectKey, setProjectKey] = useState(connector.project_key || '');
  const [syncDirection, setSyncDirection] = useState(connector.sync_direction);
  const [syncFrequency, setSyncFrequency] = useState(connector.sync_frequency);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(connector.connector_id, {
        instance_url: instanceUrl,
        project_key: projectKey,
        sync_direction: syncDirection,
        sync_frequency: syncFrequency,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    clearTestResult();
    await onTestConnection(connector.connector_id, instanceUrl, projectKey);
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
              <label className={styles.fieldLabel}>Instance URL</label>
              <input
                type="url"
                className={styles.fieldInput}
                placeholder="https://your-instance.example.com"
                value={instanceUrl}
                onChange={(e) => setInstanceUrl(e.target.value)}
              />
              <span className={styles.fieldHint}>
                The base URL of your {connector.name} instance
              </span>
            </div>

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
              disabled={testingConnection || !instanceUrl}
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

const isConnectorToggleable = (status: Connector['status']) =>
  status === 'available' || status === 'production';
