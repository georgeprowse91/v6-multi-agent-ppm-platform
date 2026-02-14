import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ConfigForm } from '@/components/config';
import { getErrorMessage, requestJson } from '@/services/apiClient';
import type { AgentConfig } from '@/store/agentConfig/types';
import styles from './AgentProfilePage.module.css';

const API_BASE = '/v1';

interface AgentProfile {
  agent_id: string;
  name: string;
  purpose: string;
  capabilities: string[];
  inputs: string[];
  outputs: string[];
  templates_touched: Array<{
    template_id: string;
    template_name: string;
    lifecycle_events: string[];
    methodology_nodes: Array<Record<string, string | null>>;
    run_modes: string[];
  }>;
  connectors_used: Array<{
    connector_type: string;
    system: string;
    category: string;
    objects: string[];
  }>;
  methodology_nodes_supported: Array<Record<string, string | null>>;
  run_modes: string[];
}

interface PreviewRunResult {
  agent_id: string;
  demo_safe: boolean;
  run_trace: Record<string, unknown>;
  artifacts: Array<Record<string, unknown>>;
  connector_operations: Array<Record<string, unknown>>;
  status: string;
}

export function AgentProfilePage() {
  const { agent_id: agentId = '' } = useParams<{ agent_id: string }>();
  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewRunResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agents, profilePayload] = await Promise.all([
        requestJson<AgentConfig[]>(`${API_BASE}/agents/config`),
        requestJson<AgentProfile>(`/api/agent-gallery/agents/${agentId}`),
      ]);
      setProfile(profilePayload);
      setAgentConfig(agents.find((agent) => agent.agent_id === agentId) ?? null);
    } catch (fetchError) {
      setError(getErrorMessage(fetchError, 'Unable to load agent profile.'));
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void fetchProfile();
  }, [fetchProfile]);

  const fields = useMemo(() => {
    if (!agentConfig) return [];
    return [
      { name: 'enabled', label: 'Enabled', type: 'boolean' as const },
      ...agentConfig.parameters.map((parameter) => ({
        name: parameter.name,
        label: parameter.display_name,
        description: parameter.description,
        type: parameter.param_type === 'string' ? 'text' as const : parameter.param_type,
        options: parameter.options,
        required: parameter.required,
      })),
    ];
  }, [agentConfig]);

  const initialValues = useMemo(() => {
    if (!agentConfig) return {};
    return agentConfig.parameters.reduce<Record<string, unknown>>(
      (acc, parameter) => {
        acc[parameter.name] = parameter.current_value ?? parameter.default_value;
        return acc;
      },
      { enabled: agentConfig.enabled }
    );
  }, [agentConfig]);

  const saveConfig = async (values: Record<string, unknown>) => {
    if (!agentConfig) return;
    const updatedParameters = agentConfig.parameters.map((parameter) => ({
      ...parameter,
      current_value: values[parameter.name],
    }));
    await requestJson<AgentConfig>(`${API_BASE}/agents/config/${agentConfig.catalog_id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        enabled: Boolean(values.enabled),
        parameters: updatedParameters,
      }),
    });
    setMessage('Agent configuration saved.');
    await fetchProfile();
  };

  const runPreview = async () => {
    setPreviewLoading(true);
    setMessage(null);
    try {
      const result = await requestJson<PreviewRunResult>(`/api/agent-gallery/agents/${agentId}/run-preview`, {
        method: 'POST',
        body: JSON.stringify({ lifecycle_event: 'generate' }),
      });
      setPreview(result);
      setMessage('Demo-safe run preview completed.');
    } catch (runError) {
      setMessage(getErrorMessage(runError, 'Preview run failed.'));
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return <div className={styles.page}>Loading agent profile…</div>;
  }

  if (error || !profile) {
    return (
      <div className={styles.page}>
        <p>{error ?? 'Agent profile unavailable.'}</p>
        <button type="button" onClick={() => void fetchProfile()}>Retry</button>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Link to="/config/agents" className={styles.backLink}>← Back to agents</Link>
      <h1>{profile.name}</h1>
      <p>{profile.purpose}</p>
      {message && <p className={styles.message}>{message}</p>}

      <section className={styles.section}>
        <h2>Capabilities</h2>
        <ul>{profile.capabilities.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Inputs</h3>
        <ul>{profile.inputs.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Outputs</h3>
        <ul>{profile.outputs.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Run modes</h3>
        <p>{profile.run_modes.join(', ') || '—'}</p>
      </section>

      <section className={styles.section}>
        <h2>Templates touched</h2>
        <ul>
          {profile.templates_touched.map((template) => (
            <li key={template.template_id}>
              <strong>{template.template_name}</strong> ({template.template_id}) — events: {template.lifecycle_events.join(', ') || '—'}
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2>Connectors used</h2>
        <ul>
          {profile.connectors_used.map((connector) => (
            <li key={`${connector.connector_type}-${connector.system}`}>
              {connector.connector_type} / {connector.system} ({connector.category})
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.section}>
        <h2>Methodology nodes supported</h2>
        <ul>
          {profile.methodology_nodes_supported.map((node) => (
            <li key={`${node.methodology_id}-${node.stage_id}-${node.activity_id ?? 'none'}-${node.task_id ?? 'none'}-${node.lifecycle_event}`}>
              {node.methodology_id} / {node.stage_id} / {node.activity_id ?? '—'} / {node.lifecycle_event}
            </li>
          ))}
        </ul>
      </section>

      {agentConfig && (
        <section className={styles.section}>
          <h2>Configure</h2>
          <ConfigForm
            title={agentConfig.display_name}
            description="Update agent parameters and enablement."
            fields={fields}
            initialValues={initialValues}
            submitLabel="Save"
            onSubmit={saveConfig}
          />
        </section>
      )}

      <section className={styles.section}>
        <h2>Run preview (demo-safe)</h2>
        <button type="button" onClick={runPreview} disabled={previewLoading}>
          {previewLoading ? 'Running…' : 'Run preview'}
        </button>
        {preview && (
          <div className={styles.previewBlock}>
            <p>Status: {preview.status}</p>
            <pre>{JSON.stringify(preview.run_trace, null, 2)}</pre>
            <h3>Artifacts</h3>
            <pre>{JSON.stringify(preview.artifacts, null, 2)}</pre>
          </div>
        )}
      </section>
    </div>
  );
}

export default AgentProfilePage;
