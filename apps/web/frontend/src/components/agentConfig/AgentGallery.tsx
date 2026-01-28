/**
 * AgentGallery - Agent configuration gallery page
 *
 * Features:
 * - List agents by category
 * - Search and filter functionality
 * - Enable/disable agents per project
 * - Open configuration modal for detailed settings
 */

import { useEffect, useMemo } from 'react';
import { useAgentConfigStore, CATEGORY_INFO, type AgentConfig, type AgentCategory } from '@/store/agentConfig';
import styles from './AgentGallery.module.css';

interface AgentGalleryProps {
  projectId?: string;
}

export function AgentGallery({ projectId = 'project-apollo' }: AgentGalleryProps) {
  const {
    agents,
    agentsLoading,
    agentsError,
    filter,
    canConfigure,
    currentUser,
    fetchAgents,
    fetchProjectConfigs,
    setCurrentUser,
    setFilter,
    resetFilter,
    getFilteredAgents,
    toggleAgentEnabled,
    isAgentEnabledForProject,
    setProjectAgentEnabled,
    openAgentModal,
    isModalOpen,
    selectedAgent,
    closeAgentModal,
    saveAgentConfig,
  } = useAgentConfigStore();

  // Initialize store
  useEffect(() => {
    fetchAgents();
    setCurrentUser('admin'); // Default to admin for demo
    if (projectId) {
      fetchProjectConfigs(projectId);
    }
  }, [fetchAgents, setCurrentUser, fetchProjectConfigs, projectId]);

  // Get filtered agents
  const filteredAgents = useMemo(() => getFilteredAgents(), [agents, filter, getFilteredAgents]);

  // Group agents by category
  const agentsByCategory = useMemo(() => {
    const grouped: Record<AgentCategory, AgentConfig[]> = {
      core: [],
      portfolio: [],
      delivery: [],
      operations: [],
      platform: [],
      governance: [],
    };
    filteredAgents.forEach((agent) => {
      const category = agent.category as AgentCategory;
      if (grouped[category]) {
        grouped[category].push(agent);
      }
    });
    return grouped;
  }, [filteredAgents]);

  // Get categories that have agents
  const activeCategories = useMemo(() => {
    return (Object.keys(agentsByCategory) as AgentCategory[]).filter(
      (cat) => agentsByCategory[cat].length > 0
    );
  }, [agentsByCategory]);

  const handleToggleEnabled = async (agent: AgentConfig) => {
    if (!canConfigure) return;
    if (projectId) {
      const currentEnabled = isAgentEnabledForProject(projectId, agent.agent_id);
      await setProjectAgentEnabled(projectId, agent.agent_id, !currentEnabled);
    } else {
      await toggleAgentEnabled(agent.catalog_id);
    }
  };

  const handleOpenConfig = (agent: AgentConfig) => {
    if (!canConfigure) return;
    openAgentModal(agent);
  };

  if (agentsLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading agents...</div>
      </div>
    );
  }

  if (agentsError && agents.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <p>Error loading agents: {agentsError}</p>
          <button onClick={fetchAgents}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>Agent Gallery</h1>
          <p className={styles.subtitle}>
            Configure AI agents for your project. Enable, disable, or customize agent behavior.
          </p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.userInfo}>
            Logged in as: <strong>{currentUser?.name || 'Unknown'}</strong> ({currentUser?.role})
          </span>
          {!canConfigure && (
            <span className={styles.readOnly}>Read-only mode</span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchBox}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search agents..."
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
          onChange={(e) => setFilter({ category: e.target.value as AgentCategory | 'all' })}
        >
          <option value="all">All Categories</option>
          {Object.values(CATEGORY_INFO).map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.icon} {cat.label}
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

        <select
          className={styles.sortSelect}
          value={filter.sortBy}
          onChange={(e) => setFilter({ sortBy: e.target.value as 'name' | 'category' | 'status' })}
        >
          <option value="name">Sort by Name</option>
          <option value="category">Sort by Category</option>
          <option value="status">Sort by Status</option>
        </select>

        <button className={styles.resetButton} onClick={resetFilter}>
          Reset Filters
        </button>
      </div>

      {/* Stats */}
      <div className={styles.stats}>
        <span>
          Showing {filteredAgents.length} of {agents.length} agents
        </span>
        <span>
          {agents.filter((a) => a.enabled).length} enabled globally
        </span>
      </div>

      {/* Agent List by Category */}
      <div className={styles.agentList}>
        {activeCategories.length === 0 ? (
          <div className={styles.empty}>
            <p>No agents match your filters.</p>
          </div>
        ) : (
          activeCategories.map((category) => (
            <CategorySection
              key={category}
              category={category}
              agents={agentsByCategory[category]}
              projectId={projectId}
              canConfigure={canConfigure}
              onToggleEnabled={handleToggleEnabled}
              onOpenConfig={handleOpenConfig}
              isAgentEnabledForProject={isAgentEnabledForProject}
            />
          ))
        )}
      </div>

      {/* Config Modal */}
      {isModalOpen && selectedAgent && (
        <AgentConfigModal
          agent={selectedAgent}
          onClose={closeAgentModal}
          onSave={saveAgentConfig}
          canConfigure={canConfigure}
        />
      )}
    </div>
  );
}

/**
 * Category section component
 */
interface CategorySectionProps {
  category: AgentCategory;
  agents: AgentConfig[];
  projectId?: string;
  canConfigure: boolean;
  onToggleEnabled: (agent: AgentConfig) => void;
  onOpenConfig: (agent: AgentConfig) => void;
  isAgentEnabledForProject: (projectId: string, agentId: string) => boolean;
}

function CategorySection({
  category,
  agents,
  projectId,
  canConfigure,
  onToggleEnabled,
  onOpenConfig,
  isAgentEnabledForProject,
}: CategorySectionProps) {
  const info = CATEGORY_INFO[category];

  return (
    <section className={styles.categorySection}>
      <div className={styles.categoryHeader}>
        <span className={styles.categoryIcon}>{info.icon}</span>
        <div className={styles.categoryInfo}>
          <h2 className={styles.categoryTitle}>{info.label}</h2>
          <p className={styles.categoryDescription}>{info.description}</p>
        </div>
        <span className={styles.categoryCount}>{agents.length} agents</span>
      </div>

      <div className={styles.agentGrid}>
        {agents.map((agent) => (
          <AgentCard
            key={agent.catalog_id}
            agent={agent}
            projectId={projectId}
            canConfigure={canConfigure}
            onToggleEnabled={() => onToggleEnabled(agent)}
            onOpenConfig={() => onOpenConfig(agent)}
            isEnabled={
              projectId
                ? isAgentEnabledForProject(projectId, agent.agent_id)
                : agent.enabled
            }
          />
        ))}
      </div>
    </section>
  );
}

/**
 * Agent card component
 */
interface AgentCardProps {
  agent: AgentConfig;
  projectId?: string;
  canConfigure: boolean;
  onToggleEnabled: () => void;
  onOpenConfig: () => void;
  isEnabled: boolean;
}

function AgentCard({
  agent,
  canConfigure,
  onToggleEnabled,
  onOpenConfig,
  isEnabled,
}: AgentCardProps) {
  const hasParameters = agent.parameters.length > 0;

  return (
    <div className={`${styles.agentCard} ${!isEnabled ? styles.disabled : ''}`}>
      <div className={styles.cardHeader}>
        <h3 className={styles.agentName}>{agent.display_name}</h3>
        <label className={styles.toggleSwitch} title={canConfigure ? 'Toggle enabled' : 'Read-only'}>
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={onToggleEnabled}
            disabled={!canConfigure}
          />
          <span className={styles.toggleSlider}></span>
        </label>
      </div>

      <p className={styles.agentDescription}>{agent.description}</p>

      <div className={styles.agentMeta}>
        <span className={styles.agentId}>{agent.agent_id}</span>
        {hasParameters && (
          <span className={styles.paramCount}>
            {agent.parameters.length} parameter{agent.parameters.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {agent.capabilities.length > 0 && (
        <div className={styles.capabilities}>
          {agent.capabilities.slice(0, 3).map((cap) => (
            <span key={cap} className={styles.capability}>
              {cap.replace(/_/g, ' ')}
            </span>
          ))}
          {agent.capabilities.length > 3 && (
            <span className={styles.moreCapabilities}>
              +{agent.capabilities.length - 3} more
            </span>
          )}
        </div>
      )}

      <div className={styles.cardActions}>
        {hasParameters && (
          <button
            className={styles.configButton}
            onClick={onOpenConfig}
            disabled={!canConfigure}
            title={canConfigure ? 'Configure agent' : 'Read-only'}
          >
            Configure
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Agent configuration modal component
 */
interface AgentConfigModalProps {
  agent: AgentConfig;
  onClose: () => void;
  onSave: (catalogId: string, parameters: AgentConfig['parameters']) => void;
  canConfigure: boolean;
}

function AgentConfigModal({ agent, onClose, onSave, canConfigure }: AgentConfigModalProps) {
  // Local state for parameter editing
  const [parameters, setParameters] = useState(
    agent.parameters.map((p) => ({
      ...p,
      current_value: p.current_value ?? p.default_value,
    }))
  );

  const handleParameterChange = (name: string, value: unknown) => {
    setParameters((params) =>
      params.map((p) => (p.name === name ? { ...p, current_value: value } : p))
    );
  };

  const handleSave = () => {
    onSave(agent.catalog_id, parameters);
  };

  const handleReset = () => {
    setParameters(
      agent.parameters.map((p) => ({
        ...p,
        current_value: p.default_value,
      }))
    );
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>{agent.display_name}</h2>
          <button className={styles.modalClose} onClick={onClose}>
            x
          </button>
        </div>

        <div className={styles.modalBody}>
          <p className={styles.modalDescription}>{agent.description}</p>

          {parameters.length === 0 ? (
            <p className={styles.noParams}>This agent has no configurable parameters.</p>
          ) : (
            <div className={styles.parameterList}>
              {parameters.map((param) => (
                <ParameterField
                  key={param.name}
                  parameter={param}
                  onChange={(value) => handleParameterChange(param.name, value)}
                  disabled={!canConfigure}
                />
              ))}
            </div>
          )}
        </div>

        <div className={styles.modalFooter}>
          <button className={styles.resetParamsButton} onClick={handleReset} disabled={!canConfigure}>
            Reset to Defaults
          </button>
          <div className={styles.modalActions}>
            <button className={styles.cancelButton} onClick={onClose}>
              Cancel
            </button>
            <button
              className={styles.saveButton}
              onClick={handleSave}
              disabled={!canConfigure}
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Parameter field component
 */
interface ParameterFieldProps {
  parameter: AgentConfig['parameters'][0] & { current_value: unknown };
  onChange: (value: unknown) => void;
  disabled: boolean;
}

function ParameterField({ parameter, onChange, disabled }: ParameterFieldProps) {
  const renderInput = () => {
    switch (parameter.param_type) {
      case 'number':
        return (
          <input
            type="number"
            className={styles.paramInput}
            value={parameter.current_value as number}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            min={parameter.min_value}
            max={parameter.max_value}
            disabled={disabled}
          />
        );

      case 'boolean':
        return (
          <label className={styles.paramCheckbox}>
            <input
              type="checkbox"
              checked={parameter.current_value as boolean}
              onChange={(e) => onChange(e.target.checked)}
              disabled={disabled}
            />
            <span>{parameter.current_value ? 'Enabled' : 'Disabled'}</span>
          </label>
        );

      case 'select':
        return (
          <select
            className={styles.paramSelect}
            value={parameter.current_value as string}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          >
            {parameter.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        return (
          <select
            className={styles.paramSelect}
            value={parameter.current_value as string[]}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions, (opt) => opt.value);
              onChange(selected);
            }}
            multiple
            disabled={disabled}
          >
            {parameter.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );

      default:
        return (
          <input
            type="text"
            className={styles.paramInput}
            value={parameter.current_value as string}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        );
    }
  };

  return (
    <div className={styles.parameterField}>
      <div className={styles.paramHeader}>
        <label className={styles.paramLabel}>{parameter.display_name}</label>
        {parameter.required && <span className={styles.required}>*</span>}
      </div>
      <p className={styles.paramDescription}>{parameter.description}</p>
      {renderInput()}
      {parameter.param_type === 'number' && (
        <span className={styles.paramRange}>
          Range: {parameter.min_value} - {parameter.max_value}
        </span>
      )}
    </div>
  );
}

// Need to import useState for the modal
import { useState } from 'react';

export default AgentGallery;
