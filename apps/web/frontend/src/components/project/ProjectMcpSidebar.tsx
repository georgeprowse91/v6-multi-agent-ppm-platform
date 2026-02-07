import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '@/store';
import { useConnectorStore } from '@/store/connectors';
import type { Connector } from '@/store/connectors/types';
import { canManageConfig } from '@/auth/permissions';
import styles from './ProjectMcpSidebar.module.css';

const API_BASE = '/v1';

interface McpToolSchema {
  name: string;
  description?: string;
  input_schema?: Record<string, unknown>;
}

interface McpToolResponse {
  system: string;
  server_id: string;
  server_url: string;
  tools: McpToolSchema[];
}

interface McpSystemState {
  enabled: boolean;
  serverUrl: string;
  serverId: string;
  toolMap: Record<string, string>;
  availableTools: McpToolSchema[];
  loadingTools: boolean;
  saving: boolean;
  error: string | null;
}

const DEFAULT_TOOL_FALLBACK = 'Select a tool';

export function ProjectMcpSidebar() {
  const { currentSelection, session } = useAppStore();
  const projectId = currentSelection?.type === 'project' ? currentSelection.id : null;
  const canManage = canManageConfig(session.user?.permissions);
  const { projectConnectors, fetchProjectConnectors, disableProjectConnector } = useConnectorStore();
  const connectors = projectId ? projectConnectors[projectId] ?? [] : [];

  const mcpSystems = useMemo(
    () => connectors.filter((connector) => connector.connector_type === 'mcp'),
    [connectors]
  );

  const [systemState, setSystemState] = useState<Record<string, McpSystemState>>({});
  const stateRef = useRef(systemState);

  useEffect(() => {
    stateRef.current = systemState;
  }, [systemState]);

  useEffect(() => {
    if (projectId) {
      fetchProjectConnectors(projectId);
    }
  }, [fetchProjectConnectors, projectId]);

  const syncSystemState = useCallback((connector: Connector) => {
    setSystemState((prev) => {
      const nextToolMap = Object.entries(connector.mcp_tool_map ?? {}).reduce<Record<string, string>>(
        (acc, [operation, tool]) => {
          acc[operation] = String(tool ?? '');
          return acc;
        },
        {}
      );
      const existing = prev[connector.system];
      return {
        ...prev,
        [connector.system]: {
          enabled: connector.mcp_enabled ?? true,
          serverUrl: connector.mcp_server_url ?? '',
          serverId: connector.mcp_server_id ?? connector.system,
          toolMap: nextToolMap,
          availableTools: existing?.availableTools ?? [],
          loadingTools: existing?.loadingTools ?? false,
          saving: existing?.saving ?? false,
          error: existing?.error ?? null,
        },
      };
    });
  }, []);

  useEffect(() => {
    mcpSystems.forEach((connector) => syncSystemState(connector));
  }, [mcpSystems, syncSystemState]);

  useEffect(() => {
    mcpSystems.forEach((connector) => {
      const state = systemState[connector.system];
      if (!state || state.loadingTools || state.availableTools.length > 0) return;
      if (state.serverUrl) {
        loadTools(connector.system);
      }
    });
  }, [loadTools, mcpSystems, systemState]);

  const loadTools = useCallback(
    async (system: string) => {
      if (!projectId) return;
      setSystemState((prev) => ({
        ...prev,
        [system]: {
          ...(prev[system] ?? {
            enabled: true,
            serverUrl: '',
            serverId: system,
            toolMap: {},
            availableTools: [],
            loadingTools: false,
            saving: false,
            error: null,
          }),
          loadingTools: true,
          error: null,
        },
      }));
      try {
        const response = await fetch(`${API_BASE}/mcp/servers/${system}/tools`);
        if (!response.ok) {
          throw new Error(`Failed to load MCP tools: ${response.statusText}`);
        }
        const data: McpToolResponse = await response.json();
        setSystemState((prev) => ({
          ...prev,
          [system]: {
            ...(prev[system] ?? {
              enabled: true,
              serverUrl: '',
              serverId: system,
              toolMap: {},
              availableTools: [],
              loadingTools: false,
              saving: false,
              error: null,
            }),
            availableTools: data.tools ?? [],
            serverUrl: data.server_url ?? prev[system]?.serverUrl ?? '',
            serverId: data.server_id ?? prev[system]?.serverId ?? system,
            loadingTools: false,
          },
        }));
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load MCP tools';
        setSystemState((prev) => ({
          ...prev,
          [system]: {
            ...(prev[system] ?? {
              enabled: true,
              serverUrl: '',
              serverId: system,
              toolMap: {},
              availableTools: [],
              loadingTools: false,
              saving: false,
              error: null,
            }),
            loadingTools: false,
            error: message,
          },
        }));
      }
    },
    [projectId]
  );

  const handleToggle = async (connector: Connector, enabled: boolean) => {
    if (!projectId) return;
    if (!enabled) {
      await disableProjectConnector(projectId, connector.connector_id);
      setSystemState((prev) => ({
        ...prev,
        [connector.system]: {
          ...prev[connector.system],
          enabled: false,
        },
      }));
      return;
    }
    setSystemState((prev) => ({
      ...prev,
      [connector.system]: {
        ...prev[connector.system],
        enabled,
      },
    }));
    await persistConfig(connector.system, { enabled });
  };

  const handleToolChange = (system: string, operation: string, tool: string) => {
    setSystemState((prev) => ({
      ...prev,
      [system]: {
        ...prev[system],
        toolMap: {
          ...prev[system]?.toolMap,
          [operation]: tool,
        },
      },
    }));
  };

  const persistConfig = async (
    system: string,
    overrides?: { enabled?: boolean; toolMap?: Record<string, string> }
  ) => {
    if (!projectId) return;
    setSystemState((prev) => ({
      ...prev,
      [system]: {
        ...prev[system],
        saving: true,
        error: null,
      },
    }));
    try {
      const state = stateRef.current[system];
      if (!state) {
        throw new Error('MCP system not initialized');
      }
      if (!state.serverUrl) {
        throw new Error('Missing MCP server URL for this system.');
      }
      const toolMap = overrides?.toolMap ?? state.toolMap;
      const payload = {
        mcp_server_url: state.serverUrl,
        mcp_server_id: state.serverId || system,
        mcp_tool_map: toolMap,
      };
      const method = overrides?.enabled ? 'POST' : 'PUT';
      const response = await fetch(`/api/projects/${projectId}/connectors/${system}/mcp`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to save MCP config: ${response.statusText}`);
      }
      await response.json();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save MCP config';
      setSystemState((prev) => ({
        ...prev,
        [system]: {
          ...prev[system],
          error: message,
        },
      }));
    } finally {
      setSystemState((prev) => ({
        ...prev,
        [system]: {
          ...prev[system],
          saving: false,
        },
      }));
    }
  };

  const handleSaveToolMap = async (system: string) => {
    const state = stateRef.current[system];
    if (!state) return;
    if (!state.serverUrl) {
      setSystemState((prev) => ({
        ...prev,
        [system]: {
          ...prev[system],
          error: 'Missing MCP server URL for this system.',
        },
      }));
      return;
    }
    const cleanedMap = Object.entries(state.toolMap).reduce<Record<string, string>>(
      (acc, [operation, tool]) => {
        if (tool && tool !== DEFAULT_TOOL_FALLBACK) {
          acc[operation] = tool;
        }
        return acc;
      },
      {}
    );
    await persistConfig(system, { toolMap: cleanedMap });
  };

  if (!projectId) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>Select a project workspace to configure MCP.</div>
      </div>
    );
  }

  if (!mcpSystems.length) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>No MCP-enabled systems are configured for this project.</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {mcpSystems.map((connector) => {
        const state = systemState[connector.system];
        if (!state) return null;
        const operations = connector.supported_operations.length
          ? connector.supported_operations
          : Object.keys(state.toolMap);
        return (
          <div key={connector.system} className={styles.systemCard}>
            <div className={styles.systemHeader}>
              <div className={styles.systemTitleRow}>
                <span className={styles.systemTitle}>{connector.name}</span>
                <span
                  className={`${styles.statusBadge} ${
                    state.enabled ? styles.statusEnabled : styles.statusDisabled
                  }`}
                >
                  {state.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className={styles.systemMeta}>
                System: {connector.system} · MCP Server: {state.serverId || 'Not set'}
              </div>
            </div>

            <div className={styles.actions}>
              <label>
                <input
                  type="checkbox"
                  checked={state.enabled}
                  onChange={(event) => handleToggle(connector, event.target.checked)}
                  disabled={!canManage}
                />{' '}
                Enable MCP for this system
              </label>
              <button
                className={styles.actionButton}
                onClick={() => loadTools(connector.system)}
                disabled={state.loadingTools}
              >
                {state.loadingTools ? 'Loading…' : 'Refresh tools'}
              </button>
            </div>

            {state.error && <div className={styles.errorText}>{state.error}</div>}
            {state.loadingTools && (
              <div className={styles.loadingText}>Fetching MCP tools...</div>
            )}

            <div className={styles.toolMap}>
              {(operations.length ? operations : ['projects.read', 'projects.write']).map(
                (operation) => (
                  <div key={operation} className={styles.toolRow}>
                    <label className={styles.toolLabel} htmlFor={`${connector.system}-${operation}`}>
                      {operation}
                    </label>
                    <select
                      id={`${connector.system}-${operation}`}
                      className={styles.toolSelect}
                      value={state.toolMap[operation] ?? ''}
                      onChange={(event) =>
                        handleToolChange(connector.system, operation, event.target.value)
                      }
                      disabled={!canManage || !state.enabled}
                    >
                      <option value="">{DEFAULT_TOOL_FALLBACK}</option>
                      {state.availableTools.map((tool) => (
                        <option key={tool.name} value={tool.name}>
                          {tool.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )
              )}
            </div>

            {state.availableTools.length > 0 && (
              <div className={styles.toolList}>
                {state.availableTools.map((tool) => (
                  <div key={tool.name} className={styles.toolItem}>
                    <div className={styles.toolName}>{tool.name}</div>
                    {tool.description && (
                      <div className={styles.toolDescription}>{tool.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className={styles.actions}>
              <button
                className={styles.actionButton}
                onClick={() => handleSaveToolMap(connector.system)}
                disabled={!canManage || state.saving}
              >
                {state.saving ? 'Saving…' : 'Save MCP mappings'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
