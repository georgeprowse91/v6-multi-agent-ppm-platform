import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ConfigForm } from '@/components/config';
import type { AgentConfig, AgentParameter } from '@/store/agentConfig/types';
import type { ConfigField, Connector } from '@/store/connectors/types';
import styles from './ConfigPage.module.css';

const API_BASE = '/v1';

type ConfigType = 'agents' | 'connectors' | 'workflows';

interface ConfigPageProps {
  type: ConfigType;
}

interface OrchestrationRoutingEntry {
  agent_id: string;
  action?: string | null;
  depends_on?: string[];
  intent?: string | null;
  priority?: number | null;
}

interface OrchestrationConfig {
  default_routing: OrchestrationRoutingEntry[];
  last_updated_by: string;
}

const configTabs: Record<ConfigType, { label: string; description: string }> = {
  agents: {
    label: 'Agents',
    description: 'Tune agent enablement and parameters for your orchestration layer.',
  },
  connectors: {
    label: 'Connectors',
    description: 'Configure integration endpoints, sync settings, and custom fields.',
  },
  workflows: {
    label: 'Workflows',
    description: 'Maintain orchestration routing rules for workflow execution.',
  },
};

const syncDirectionOptions = ['inbound', 'outbound', 'bidirectional'];
const syncFrequencyOptions = [
  'realtime',
  'hourly',
  'every_4_hours',
  'daily',
  'weekly',
  'manual',
];

const agentMaturityByCategory: Record<string, string> = {
  core: 'Production',
  portfolio: 'Beta',
  delivery: 'Beta',
  operations: 'Production',
  platform: 'Production',
  governance: 'Beta',
};

const toConfigFieldType = (
  type: ConfigField['type'] | AgentParameter['param_type']
) => {
  switch (type) {
    case 'number':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'select':
      return 'select';
    case 'multiselect':
      return 'multiselect';
    case 'url':
      return 'url';
    default:
      return 'text';
  }
};

export function ConfigPage({ type }: ConfigPageProps) {
  const [activeTab, setActiveTab] = useState<ConfigType>(type);

  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);

  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [connectorsLoading, setConnectorsLoading] = useState(true);
  const [connectorsError, setConnectorsError] = useState<string | null>(null);

  const [workflowConfig, setWorkflowConfig] = useState<OrchestrationConfig | null>(null);
  const [routingEntries, setRoutingEntries] = useState<OrchestrationRoutingEntry[]>([]);
  const [workflowsLoading, setWorkflowsLoading] = useState(true);
  const [workflowsError, setWorkflowsError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);
  const [selectedWorkflowIndex, setSelectedWorkflowIndex] = useState<number | null>(null);

  useEffect(() => {
    setActiveTab(type);
  }, [type]);

  const fetchAgents = useCallback(async () => {
    setAgentsLoading(true);
    setAgentsError(null);
    try {
      const response = await fetch(`${API_BASE}/agents/config`);
      if (!response.ok) {
        throw new Error(`Failed to load agents: ${response.statusText}`);
      }
      const data = (await response.json()) as AgentConfig[];
      setAgents(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load agents.';
      setAgentsError(message);
      setAgents([]);
    } finally {
      setAgentsLoading(false);
    }
  }, []);

  const fetchConnectors = useCallback(async () => {
    setConnectorsLoading(true);
    setConnectorsError(null);
    try {
      const response = await fetch(`${API_BASE}/connectors`);
      if (!response.ok) {
        throw new Error(`Failed to load connectors: ${response.statusText}`);
      }
      const data = (await response.json()) as Connector[];
      setConnectors(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load connectors.';
      setConnectorsError(message);
      setConnectors([]);
    } finally {
      setConnectorsLoading(false);
    }
  }, []);

  const fetchWorkflows = useCallback(async () => {
    setWorkflowsLoading(true);
    setWorkflowsError(null);
    try {
      const response = await fetch(`${API_BASE}/orchestration/config`);
      if (!response.ok) {
        throw new Error(`Failed to load workflows: ${response.statusText}`);
      }
      const data = (await response.json()) as OrchestrationConfig;
      setWorkflowConfig(data);
      setRoutingEntries(data.default_routing ?? []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load workflows.';
      setWorkflowsError(message);
      setWorkflowConfig(null);
      setRoutingEntries([]);
    } finally {
      setWorkflowsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchConnectors();
    fetchWorkflows();
  }, [fetchAgents, fetchConnectors, fetchWorkflows]);

  const tabs = useMemo(
    () =>
      (Object.keys(configTabs) as ConfigType[]).map((key) => ({
        key,
        ...configTabs[key],
      })),
    []
  );

  const handleAgentSubmit = async (agent: AgentConfig, values: Record<string, unknown>) => {
    const updatedParameters = agent.parameters.map((parameter) => ({
      ...parameter,
      current_value: values[parameter.name],
    }));

    const payload = {
      enabled: Boolean(values.enabled),
      parameters: updatedParameters,
    };

    const response = await fetch(`${API_BASE}/agents/config/${agent.catalog_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to update ${agent.display_name}.`);
    }

    let updatedAgent: AgentConfig | null = null;
    try {
      updatedAgent = (await response.json()) as AgentConfig;
    } catch {
      updatedAgent = null;
    }

    setAgents((prev) =>
      prev.map((entry) =>
        entry.catalog_id === agent.catalog_id
          ? updatedAgent ?? { ...agent, ...payload }
          : entry
      )
    );
  };

  const handleConnectorSubmit = async (connector: Connector, values: Record<string, unknown>) => {
    const customFields = connector.config_fields.reduce<Record<string, unknown>>(
      (acc, field) => {
        const value = values[field.name];
        if (Array.isArray(value)) {
          if (value.length > 0) {
            acc[field.name] = value;
          }
          return acc;
        }
        if (value !== undefined && value !== '') {
          acc[field.name] = value;
        }
        return acc;
      },
      {}
    );

    const payload: Record<string, unknown> = {
      instance_url: values.instance_url || undefined,
      project_key: values.project_key || undefined,
      sync_direction: values.sync_direction || undefined,
      sync_frequency: values.sync_frequency || undefined,
      custom_fields: Object.keys(customFields).length ? customFields : undefined,
    };

    const response = await fetch(`${API_BASE}/connectors/${connector.connector_id}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to update ${connector.name}.`);
    }

    setConnectors((prev) =>
      prev.map((entry) =>
        entry.connector_id === connector.connector_id
          ? {
              ...entry,
              instance_url: String(values.instance_url ?? entry.instance_url),
              project_key: String(values.project_key ?? entry.project_key),
              sync_direction: (values.sync_direction as Connector['sync_direction']) ??
                entry.sync_direction,
              sync_frequency: (values.sync_frequency as Connector['sync_frequency']) ??
                entry.sync_frequency,
              custom_fields: Object.keys(customFields).length
                ? customFields
                : entry.custom_fields,
            }
          : entry
      )
    );
  };

  const handleWorkflowSubmit = async (
    index: number,
    values: Record<string, unknown>
  ) => {
    const nextEntries = routingEntries.map((entry, entryIndex) => {
      if (entryIndex !== index) return entry;

      const dependsOnValue = String(values.depends_on ?? '')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);

      return {
        agent_id: String(values.agent_id ?? '').trim(),
        action: values.action ? String(values.action) : null,
        intent: values.intent ? String(values.intent) : null,
        priority:
          values.priority === '' || values.priority === undefined
            ? null
            : Number(values.priority),
        depends_on: dependsOnValue,
      };
    });

    const payload: OrchestrationConfig = {
      default_routing: nextEntries,
      last_updated_by: 'web-ui',
    };

    const response = await fetch(`${API_BASE}/orchestration/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('Failed to update workflow routing.');
    }

    const updated = (await response.json()) as OrchestrationConfig;
    setWorkflowConfig(updated);
    setRoutingEntries(updated.default_routing ?? []);
  };

  const handleAddRoutingEntry = () => {
    setRoutingEntries((prev) => [
      ...prev,
      { agent_id: '', action: null, intent: null, depends_on: [], priority: null },
    ]);
  };

  const handleCloseModal = () => {
    setSelectedAgent(null);
    setSelectedWorkflowIndex(null);
  };

  const handleTestClick = (label: string) => {
    console.info(`Testing ${label}`);
  };

  const selectedWorkflow =
    selectedWorkflowIndex !== null ? routingEntries[selectedWorkflowIndex] : null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Configuration Center</h1>
        <p className={styles.description}>
          Update connector settings, agent parameters, and workflow routing without leaving the
          console.
        </p>
      </header>

      <div className={styles.tabs} role="tablist" aria-label="Configuration tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            id={`tab-${tab.key}`}
            aria-selected={activeTab === tab.key}
            aria-controls={`tab-panel-${tab.key}`}
            className={`${styles.tabButton} ${
              activeTab === tab.key ? styles.tabActive : ''
            }`}
            onClick={() => setActiveTab(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      <section
        id={`tab-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className={styles.tabPanel}
      >
        <p className={styles.tabDescription}>{configTabs[activeTab].description}</p>

        {activeTab === 'agents' && (
          <div className={styles.section}>
            {agentsLoading && <div className={styles.state}>Loading agents…</div>}
            {agentsError && (
              <div className={styles.errorState}>
                <span>{agentsError}</span>
                <button type="button" onClick={fetchAgents}>
                  Retry
                </button>
              </div>
            )}
            {!agentsLoading && !agentsError && agents.length === 0 && (
              <div className={styles.state}>No agent configurations available.</div>
            )}
            {!agentsLoading && !agentsError && agents.length > 0 && (
              <div className={styles.cardGrid}>
                {agents.map((agent) => {
                  const maturity =
                    agentMaturityByCategory[agent.category] ?? 'Beta';
                  const estimatedCost = `$${(
                    0.04 + agent.parameters.length * 0.01
                  ).toFixed(2)}/run`;
                  const latencyEstimate = `${280 + agent.capabilities.length * 35}ms avg`;

                  const fields = [
                    {
                      name: 'enabled',
                      label: 'Enabled',
                      type: 'boolean' as const,
                      description: 'Toggle global availability for this agent.',
                    },
                    ...agent.parameters.map((parameter) => ({
                      name: parameter.name,
                      label: parameter.display_name,
                      type: toConfigFieldType(parameter.param_type),
                      description: parameter.description,
                      required: parameter.required,
                      options: parameter.options,
                      min: parameter.min_value,
                      max: parameter.max_value,
                    })),
                  ];

                  const initialValues = agent.parameters.reduce<Record<string, unknown>>(
                    (acc, parameter) => {
                      acc[parameter.name] =
                        parameter.current_value ?? parameter.default_value ?? '';
                      return acc;
                    },
                    { enabled: agent.enabled }
                  );

                  return (
                    <div key={agent.catalog_id} className={styles.card}>
                      <div className={styles.cardHeader}>
                        <div>
                          <h3 className={styles.cardTitle}>{agent.display_name}</h3>
                          <p className={styles.cardDescription}>{agent.description}</p>
                        </div>
                        <div className={styles.badges}>
                          <span
                            className={`${styles.badge} ${
                              agent.enabled ? styles.badgeOn : styles.badgeOff
                            }`}
                          >
                            {agent.enabled ? 'On' : 'Off'}
                          </span>
                          <span className={`${styles.badge} ${styles.badgeMaturity}`}>
                            {maturity}
                          </span>
                        </div>
                      </div>
                      <div className={styles.cardMeta}>
                        <div>
                          <span className={styles.metaLabel}>Estimated cost</span>
                          <span className={styles.metaValue}>{estimatedCost}</span>
                        </div>
                        <div>
                          <span className={styles.metaLabel}>Performance</span>
                          <span className={styles.metaValue}>{latencyEstimate}</span>
                        </div>
                        <div>
                          <span className={styles.metaLabel}>Parameters</span>
                          <span className={styles.metaValue}>
                            {agent.parameters.length} inputs
                          </span>
                        </div>
                      </div>
                      <div className={styles.cardActions}>
                        <button
                          type="button"
                          className={styles.primaryButton}
                          onClick={() => setSelectedAgent(agent)}
                        >
                          Configure
                        </button>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          onClick={() => handleTestClick(agent.display_name)}
                        >
                          Test
                        </button>
                      </div>
                      {selectedAgent?.catalog_id === agent.catalog_id && (
                        <div
                          className={styles.modalOverlay}
                          role="dialog"
                          aria-modal="true"
                          onClick={handleCloseModal}
                        >
                          <div
                            className={styles.modal}
                            onClick={(event) => event.stopPropagation()}
                          >
                            <div className={styles.modalHeader}>
                              <div>
                                <h2 className={styles.modalTitle}>
                                  Configure {agent.display_name}
                                </h2>
                                <p className={styles.modalDescription}>
                                  {agent.description}
                                </p>
                              </div>
                              <button
                                type="button"
                                className={styles.modalClose}
                                onClick={handleCloseModal}
                              >
                                ×
                              </button>
                            </div>
                            <div className={styles.modalBody}>
                              <ConfigForm
                                title={agent.display_name}
                                description="Update parameters and enablement for this agent."
                                fields={fields}
                                initialValues={initialValues}
                                submitLabel="Save agent"
                                onSubmit={async (values) => {
                                  await handleAgentSubmit(agent, values);
                                  handleCloseModal();
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'connectors' && (
          <div className={styles.section}>
            {connectorsLoading && <div className={styles.state}>Loading connectors…</div>}
            {connectorsError && (
              <div className={styles.errorState}>
                <span>{connectorsError}</span>
                <button type="button" onClick={fetchConnectors}>
                  Retry
                </button>
              </div>
            )}
            {!connectorsLoading && !connectorsError && connectors.length === 0 && (
              <div className={styles.state}>No connector configurations available.</div>
            )}
            {!connectorsLoading && !connectorsError && connectors.length > 0 && (
              <div className={styles.forms}>
                {connectors.map((connector) => {
                  const fields = [
                    {
                      name: 'instance_url',
                      label: 'Instance URL',
                      type: 'url' as const,
                      required: false,
                      placeholder: 'https://your-instance.example.com',
                    },
                    {
                      name: 'project_key',
                      label: 'Project Key',
                      type: 'text' as const,
                      required: false,
                      placeholder: 'PPM',
                    },
                    {
                      name: 'sync_direction',
                      label: 'Sync Direction',
                      type: 'select' as const,
                      options: syncDirectionOptions,
                    },
                    {
                      name: 'sync_frequency',
                      label: 'Sync Frequency',
                      type: 'select' as const,
                      options: syncFrequencyOptions,
                    },
                    ...connector.config_fields.map((field) => ({
                      name: field.name,
                      label: field.label,
                      type: toConfigFieldType(field.type),
                      required: field.required,
                      options: field.options,
                    })),
                  ];

                  const initialValues: Record<string, unknown> = {
                    instance_url: connector.instance_url,
                    project_key: connector.project_key,
                    sync_direction: connector.sync_direction,
                    sync_frequency: connector.sync_frequency,
                    ...(connector.custom_fields ?? {}),
                  };

                  return (
                    <ConfigForm
                      key={connector.connector_id}
                      title={connector.name}
                      description={connector.description}
                      fields={fields}
                      initialValues={initialValues}
                      submitLabel="Update connector"
                      onSubmit={(values) => handleConnectorSubmit(connector, values)}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className={styles.section}>
            {workflowsLoading && <div className={styles.state}>Loading workflows…</div>}
            {workflowsError && (
              <div className={styles.errorState}>
                <span>{workflowsError}</span>
                <button type="button" onClick={fetchWorkflows}>
                  Retry
                </button>
              </div>
            )}
            {!workflowsLoading && !workflowsError && (
              <div className={styles.workflowHeader}>
                <div>
                  <h2 className={styles.workflowTitle}>Default Routing Rules</h2>
                  <p className={styles.workflowHint}>
                    Update routing entries to define how workflow requests are orchestrated, or
                    open the workflow designer to build multi-agent flows.
                  </p>
                </div>
                <div className={styles.workflowActions}>
                  <Link className={styles.secondaryButton} to="/workflows/designer">
                    Open workflow designer
                  </Link>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={handleAddRoutingEntry}
                  >
                    Add routing entry
                  </button>
                </div>
              </div>
            )}
            {!workflowsLoading && !workflowsError && routingEntries.length === 0 && (
              <div className={styles.state}>No workflow routing entries defined.</div>
            )}
            {!workflowsLoading && !workflowsError && routingEntries.length > 0 && (
              <div className={styles.cardGrid}>
                {routingEntries.map((entry, index) => {
                  const workflowName =
                    entry.intent?.replace(/_/g, ' ') ||
                    entry.action?.replace(/_/g, ' ') ||
                    `Routing entry ${index + 1}`;
                  const status = entry.agent_id ? 'On' : 'Off';
                  const maturity =
                    entry.priority !== null && entry.priority !== undefined
                      ? entry.priority <= 1
                        ? 'Production'
                        : entry.priority <= 3
                        ? 'Beta'
                        : 'Experimental'
                      : 'Beta';
                  const estimatedCost = `$${(
                    0.06 + (entry.depends_on?.length ?? 0) * 0.02
                  ).toFixed(2)}/run`;
                  const latencyEstimate = `${320 + (entry.priority ?? 2) * 85}ms target`;
                  const description = entry.agent_id
                    ? `Routes ${workflowName} requests to ${entry.agent_id}.`
                    : 'Assign an agent to activate this workflow route.';

                  return (
                    <div
                      key={`${entry.agent_id || 'entry'}-${index}`}
                      className={styles.card}
                    >
                      <div className={styles.cardHeader}>
                        <div>
                          <h3 className={styles.cardTitle}>{workflowName}</h3>
                          <p className={styles.cardDescription}>{description}</p>
                        </div>
                        <div className={styles.badges}>
                          <span
                            className={`${styles.badge} ${
                              status === 'On' ? styles.badgeOn : styles.badgeOff
                            }`}
                          >
                            {status}
                          </span>
                          <span className={`${styles.badge} ${styles.badgeMaturity}`}>
                            {maturity}
                          </span>
                        </div>
                      </div>
                      <div className={styles.cardMeta}>
                        <div>
                          <span className={styles.metaLabel}>Estimated cost</span>
                          <span className={styles.metaValue}>{estimatedCost}</span>
                        </div>
                        <div>
                          <span className={styles.metaLabel}>Performance</span>
                          <span className={styles.metaValue}>{latencyEstimate}</span>
                        </div>
                        <div>
                          <span className={styles.metaLabel}>Dependencies</span>
                          <span className={styles.metaValue}>
                            {(entry.depends_on ?? []).length} agents
                          </span>
                        </div>
                      </div>
                      <div className={styles.cardActions}>
                        <button
                          type="button"
                          className={styles.primaryButton}
                          onClick={() => setSelectedWorkflowIndex(index)}
                        >
                          Configure
                        </button>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          onClick={() => handleTestClick(workflowName)}
                        >
                          Test
                        </button>
                      </div>
                    </div>
                  );
                })}
                {selectedWorkflow && selectedWorkflowIndex !== null && (
                  <div
                    className={styles.modalOverlay}
                    role="dialog"
                    aria-modal="true"
                    onClick={handleCloseModal}
                  >
                    <div
                      className={styles.modal}
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className={styles.modalHeader}>
                        <div>
                          <h2 className={styles.modalTitle}>
                            Configure workflow routing
                          </h2>
                          <p className={styles.modalDescription}>
                            Update routing details and validation will appear inline.
                          </p>
                        </div>
                        <button
                          type="button"
                          className={styles.modalClose}
                          onClick={handleCloseModal}
                        >
                          ×
                        </button>
                      </div>
                      <div className={styles.modalBody}>
                        <ConfigForm
                          title={`Routing entry ${selectedWorkflowIndex + 1}`}
                          description={
                            workflowConfig
                              ? `Last updated by ${workflowConfig.last_updated_by}.`
                              : undefined
                          }
                          fields={[
                            {
                              name: 'agent_id',
                              label: 'Agent ID',
                              type: 'text',
                              required: true,
                              placeholder: 'intent-router',
                            },
                            {
                              name: 'action',
                              label: 'Action',
                              type: 'text',
                              placeholder: 'route',
                            },
                            {
                              name: 'intent',
                              label: 'Intent',
                              type: 'text',
                              placeholder: 'portfolio_intake',
                            },
                            {
                              name: 'priority',
                              label: 'Priority',
                              type: 'number',
                              min: 0,
                              placeholder: '1',
                            },
                            {
                              name: 'depends_on',
                              label: 'Depends On',
                              type: 'text',
                              placeholder: 'agent-1, agent-2',
                            },
                          ]}
                          initialValues={{
                            agent_id: selectedWorkflow.agent_id,
                            action: selectedWorkflow.action ?? '',
                            intent: selectedWorkflow.intent ?? '',
                            priority: selectedWorkflow.priority ?? '',
                            depends_on: (selectedWorkflow.depends_on ?? []).join(', '),
                          }}
                          submitLabel="Save routing"
                          onSubmit={async (values) => {
                            await handleWorkflowSubmit(selectedWorkflowIndex, values);
                            handleCloseModal();
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
