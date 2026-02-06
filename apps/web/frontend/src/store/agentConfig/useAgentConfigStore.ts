/**
 * Agent Configuration Store
 *
 * Zustand store for managing agent configurations,
 * project-specific settings, and user permissions.
 */

import { create } from 'zustand';
import type {
  AgentConfig,
  AgentFilterState,
  AgentParameter,
  DevUser,
  ProjectAgentConfig,
} from './types';

// API base URL - in production this would come from environment
const API_BASE = '/v1';

interface AgentConfigStoreState {
  // Agent configurations
  agents: AgentConfig[];
  agentsLoading: boolean;
  agentsError: string | null;

  // Project-specific configurations
  projectConfigs: Record<string, ProjectAgentConfig[]>;
  projectConfigsLoading: boolean;

  // Current user (dev mode)
  currentUser: DevUser | null;
  canConfigure: boolean;

  // Filter state
  filter: AgentFilterState;

  // Selected agent for modal
  selectedAgent: AgentConfig | null;
  isModalOpen: boolean;

  // Actions - Agents
  fetchAgents: () => Promise<void>;
  getAgent: (catalogId: string) => AgentConfig | undefined;
  updateAgent: (catalogId: string, updates: Partial<AgentConfig>) => Promise<void>;
  toggleAgentEnabled: (catalogId: string) => Promise<void>;

  // Actions - Project configs
  fetchProjectConfigs: (projectId: string) => Promise<void>;
  setProjectAgentEnabled: (projectId: string, agentId: string, enabled: boolean) => Promise<void>;
  isAgentEnabledForProject: (projectId: string, agentId: string) => boolean;
  getEnabledAgentsForProject: (projectId: string) => AgentConfig[];
  applyTemplateAgents: (
    projectId: string,
    config: { enabled: string[]; disabled: string[] }
  ) => void;

  // Actions - User
  setCurrentUser: (userId: string) => Promise<void>;
  checkCanConfigure: () => Promise<void>;

  // Actions - Filter
  setFilter: (filter: Partial<AgentFilterState>) => void;
  resetFilter: () => void;
  getFilteredAgents: () => AgentConfig[];

  // Actions - Modal
  openAgentModal: (agent: AgentConfig) => void;
  closeAgentModal: () => void;
  saveAgentConfig: (catalogId: string, parameters: AgentParameter[]) => Promise<void>;
}

const DEFAULT_FILTER: AgentFilterState = {
  search: '',
  category: 'all',
  enabledOnly: false,
  sortBy: 'name',
};

export const useAgentConfigStore = create<AgentConfigStoreState>((set, get) => ({
  // Initial state
  agents: [],
  agentsLoading: false,
  agentsError: null,
  projectConfigs: {},
  projectConfigsLoading: false,
  currentUser: null,
  canConfigure: false,
  filter: DEFAULT_FILTER,
  selectedAgent: null,
  isModalOpen: false,

  // Fetch all agents
  fetchAgents: async () => {
    set({ agentsLoading: true, agentsError: null });
    try {
      const response = await fetch(`${API_BASE}/agents/config`);
      if (!response.ok) {
        throw new Error(`Failed to fetch agents: ${response.statusText}`);
      }
      const data = await response.json();
      set({ agents: data, agentsLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      set({ agentsError: message, agentsLoading: false });
      // Fall back to mock data for development
      set({ agents: getMockAgents() });
    }
  },

  // Get a specific agent
  getAgent: (catalogId) => {
    return get().agents.find((a) => a.catalog_id === catalogId);
  },

  // Update agent configuration
  updateAgent: async (catalogId, updates) => {
    try {
      const response = await fetch(`${API_BASE}/agents/config/${catalogId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': get().currentUser?.user_id || 'admin',
        },
        body: JSON.stringify(updates),
      });
      if (!response.ok) {
        throw new Error(`Failed to update agent: ${response.statusText}`);
      }
      const updatedAgent = await response.json();
      set((state) => ({
        agents: state.agents.map((a) =>
          a.catalog_id === catalogId ? updatedAgent : a
        ),
      }));
    } catch (error) {
      // Update locally for development
      set((state) => ({
        agents: state.agents.map((a) =>
          a.catalog_id === catalogId ? { ...a, ...updates } : a
        ),
      }));
    }
  },

  // Toggle agent enabled state
  toggleAgentEnabled: async (catalogId) => {
    const agent = get().getAgent(catalogId);
    if (!agent) return;
    await get().updateAgent(catalogId, { enabled: !agent.enabled });
  },

  // Fetch project-specific configs
  fetchProjectConfigs: async (projectId) => {
    set({ projectConfigsLoading: true });
    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/agents/config`);
      if (!response.ok) {
        throw new Error(`Failed to fetch project configs: ${response.statusText}`);
      }
      const data = await response.json();
      set((state) => ({
        projectConfigs: {
          ...state.projectConfigs,
          [projectId]: data,
        },
        projectConfigsLoading: false,
      }));
    } catch (error) {
      set({ projectConfigsLoading: false });
      // Initialize empty for development
      set((state) => ({
        projectConfigs: {
          ...state.projectConfigs,
          [projectId]: [],
        },
      }));
    }
  },

  // Set project agent enabled state
  setProjectAgentEnabled: async (projectId, agentId, enabled) => {
    try {
      const response = await fetch(
        `${API_BASE}/projects/${projectId}/agents/config/${agentId}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': get().currentUser?.user_id || 'admin',
          },
          body: JSON.stringify({ enabled, parameter_overrides: {} }),
        }
      );
      if (!response.ok) {
        throw new Error(`Failed to set project agent config: ${response.statusText}`);
      }
      // Refresh project configs
      await get().fetchProjectConfigs(projectId);
    } catch (error) {
      // Update locally for development
      set((state) => {
        const projectConfigs = state.projectConfigs[projectId] || [];
        const existingIndex = projectConfigs.findIndex((c) => c.agent_id === agentId);
        const newConfig: ProjectAgentConfig = {
          project_id: projectId,
          agent_id: agentId,
          enabled,
          parameter_overrides: {},
        };
        if (existingIndex >= 0) {
          projectConfigs[existingIndex] = newConfig;
        } else {
          projectConfigs.push(newConfig);
        }
        return {
          projectConfigs: {
            ...state.projectConfigs,
            [projectId]: [...projectConfigs],
          },
        };
      });
    }
  },

  applyTemplateAgents: (projectId, config) => {
    set((state) => {
      const enabledSet = new Set(config.enabled);
      const disabledSet = new Set(config.disabled);
      const projectConfigs: ProjectAgentConfig[] = [
        ...Array.from(enabledSet).map((agentId) => ({
          project_id: projectId,
          agent_id: agentId,
          enabled: true,
          parameter_overrides: {},
        })),
        ...Array.from(disabledSet).map((agentId) => ({
          project_id: projectId,
          agent_id: agentId,
          enabled: false,
          parameter_overrides: {},
        })),
      ];

      return {
        projectConfigs: {
          ...state.projectConfigs,
          [projectId]: projectConfigs,
        },
      };
    });
  },

  // Check if agent is enabled for project
  isAgentEnabledForProject: (projectId, agentId) => {
    const { projectConfigs, agents } = get();
    const projectConfig = projectConfigs[projectId]?.find((c) => c.agent_id === agentId);
    if (projectConfig) {
      return projectConfig.enabled;
    }
    // Fall back to global config
    const agent = agents.find((a) => a.agent_id === agentId);
    return agent?.enabled ?? true;
  },

  // Get all enabled agents for a project
  getEnabledAgentsForProject: (projectId) => {
    const { agents } = get();
    return agents.filter((agent) =>
      get().isAgentEnabledForProject(projectId, agent.agent_id)
    );
  },

  // Set current user
  setCurrentUser: async (userId) => {
    try {
      const response = await fetch(`${API_BASE}/users/dev/${userId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch user: ${response.statusText}`);
      }
      const user = await response.json();
      set({ currentUser: user });
      await get().checkCanConfigure();
    } catch (error) {
      // Use mock user for development
      set({
        currentUser: {
          user_id: userId,
          name: userId === 'admin' ? 'PMO Admin' : 'Project Manager',
          email: `${userId}@example.com`,
          role: userId === 'admin' ? 'PMO_ADMIN' : 'PM',
          tenant_id: 'default',
        },
        canConfigure: userId === 'admin' || userId === 'pm',
      });
    }
  },

  // Check if current user can configure agents
  checkCanConfigure: async () => {
    const userId = get().currentUser?.user_id;
    if (!userId) {
      set({ canConfigure: false });
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/users/dev/${userId}/can-configure`);
      if (!response.ok) {
        throw new Error(`Failed to check permissions: ${response.statusText}`);
      }
      const data = await response.json();
      set({ canConfigure: data.can_configure_agents });
    } catch (error) {
      // Allow for development
      const role = get().currentUser?.role;
      set({ canConfigure: role === 'PMO_ADMIN' || role === 'PM' });
    }
  },

  // Set filter
  setFilter: (filter) => {
    set((state) => ({
      filter: { ...state.filter, ...filter },
    }));
  },

  // Reset filter
  resetFilter: () => {
    set({ filter: DEFAULT_FILTER });
  },

  // Get filtered and sorted agents
  getFilteredAgents: () => {
    const { agents, filter } = get();
    let filtered = [...agents];

    // Apply search filter
    if (filter.search) {
      const search = filter.search.toLowerCase();
      filtered = filtered.filter(
        (a) =>
          a.display_name.toLowerCase().includes(search) ||
          a.description.toLowerCase().includes(search) ||
          a.agent_id.toLowerCase().includes(search)
      );
    }

    // Apply category filter
    if (filter.category !== 'all') {
      filtered = filtered.filter((a) => a.category === filter.category);
    }

    // Apply enabled filter
    if (filter.enabledOnly) {
      filtered = filtered.filter((a) => a.enabled);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (filter.sortBy) {
        case 'name':
          return a.display_name.localeCompare(b.display_name);
        case 'category':
          return a.category.localeCompare(b.category);
        case 'status':
          return Number(b.enabled) - Number(a.enabled);
        default:
          return 0;
      }
    });

    return filtered;
  },

  // Open agent config modal
  openAgentModal: (agent) => {
    set({ selectedAgent: agent, isModalOpen: true });
  },

  // Close agent config modal
  closeAgentModal: () => {
    set({ selectedAgent: null, isModalOpen: false });
  },

  // Save agent configuration from modal
  saveAgentConfig: async (catalogId, parameters) => {
    await get().updateAgent(catalogId, {
      parameters: parameters.map((p) => ({
        name: p.name,
        display_name: p.display_name,
        description: p.description,
        param_type: p.param_type,
        default_value: p.default_value,
        current_value: p.current_value,
        options: p.options,
        min_value: p.min_value,
        max_value: p.max_value,
        required: p.required,
      })),
    });
    get().closeAgentModal();
  },
}));

/**
 * Mock agents for development when API is not available
 */
export function getMockAgents(): AgentConfig[] {
  return [
    {
      catalog_id: 'agent-01-intent-router',
      agent_id: 'intent-router',
      display_name: 'Intent Router',
      description: 'Routes user queries to appropriate specialized agents',
      category: 'core',
      enabled: true,
      capabilities: ['query_routing', 'intent_classification'],
      parameters: [],
    },
    {
      catalog_id: 'agent-10-schedule-planning',
      agent_id: 'schedule-planning',
      display_name: 'Schedule & Planning',
      description: 'Manages project schedules, timelines, and critical path analysis',
      category: 'delivery',
      enabled: true,
      capabilities: ['schedule_creation', 'critical_path_analysis', 'milestone_tracking'],
      parameters: [
        {
          name: 'default_task_duration',
          display_name: 'Default Task Duration (days)',
          description: 'Default duration for new tasks',
          param_type: 'number',
          default_value: 5,
          current_value: 5,
          min_value: 1,
          max_value: 90,
          required: true,
        },
        {
          name: 'critical_path_buffer',
          display_name: 'Critical Path Buffer (%)',
          description: 'Buffer percentage for critical path calculations',
          param_type: 'number',
          default_value: 10,
          current_value: 10,
          min_value: 0,
          max_value: 50,
          required: true,
        },
      ],
    },
    {
      catalog_id: 'agent-12-financial-management',
      agent_id: 'financial-management',
      display_name: 'Financial Management',
      description: 'Manages project finances, budgets, forecasts, and cost tracking',
      category: 'portfolio',
      enabled: true,
      capabilities: ['budget_management', 'cost_tracking', 'forecasting'],
      parameters: [
        {
          name: 'currency',
          display_name: 'Default Currency',
          description: 'Default currency for financial calculations',
          param_type: 'select',
          default_value: 'USD',
          current_value: 'USD',
          options: ['USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY'],
          required: true,
        },
        {
          name: 'cost_variance_threshold',
          display_name: 'Cost Variance Threshold (%)',
          description: 'Threshold for flagging cost variances',
          param_type: 'number',
          default_value: 10,
          current_value: 10,
          min_value: 1,
          max_value: 50,
          required: true,
        },
      ],
    },
    {
      catalog_id: 'agent-15-risk-issue-management',
      agent_id: 'agent_015',
      display_name: 'Risk & Issue Management',
      description: 'Identifies, assesses, and manages project risks and issues',
      category: 'operations',
      enabled: true,
      capabilities: ['risk_identification', 'risk_assessment', 'issue_tracking'],
      parameters: [
        {
          name: 'risk_assessment_method',
          display_name: 'Risk Assessment Method',
          description: 'Method for assessing risk severity',
          param_type: 'select',
          default_value: 'probability_impact',
          current_value: 'probability_impact',
          options: ['probability_impact', 'monte_carlo', 'qualitative', 'quantitative'],
          required: true,
        },
        {
          name: 'auto_escalate_high_risks',
          display_name: 'Auto-escalate High Risks',
          description: 'Automatically escalate high-severity risks',
          param_type: 'boolean',
          default_value: true,
          current_value: true,
          required: true,
        },
      ],
    },
  ];
}

export default useAgentConfigStore;
