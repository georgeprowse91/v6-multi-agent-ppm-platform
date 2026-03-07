import { useCallback, useEffect, useState } from 'react';
import { useAppStore } from '@/store';
import styles from './MethodologyEditor.module.css';

type MethodologySummary = {
  methodology_id: string;
  name: string;
  type: string;
  description: string;
  version: number;
  status: string;
  is_default: boolean;
  is_builtin: boolean;
  source: string;
};

type MethodologyPolicy = {
  allowed_methodology_ids: string[] | null;
  default_methodology_id: string | null;
  department_overrides: Record<string, { allowed_methodology_ids?: string[] }>;
  enforce_published_only: boolean;
  updated_at?: string;
};

type ImpactAnalysis = {
  methodology_id: string;
  affected_workspace_count: number;
  affected_workspaces: Array<{
    workspace_id: string;
    project_id: string;
    status: string;
  }>;
  warning: string;
};

async function apiFetch<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    published: 'var(--color-success, #22c55e)',
    draft: 'var(--color-warning, #eab308)',
    deprecated: 'var(--color-danger, #ef4444)',
    archived: 'var(--color-muted, #6b7280)',
  };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: '#fff',
        backgroundColor: colorMap[status] || colorMap.draft,
      }}
    >
      {status}
    </span>
  );
}

export default function OrganisationMethodologySettings() {
  const { session } = useAppStore();
  const [methodologies, setMethodologies] = useState<MethodologySummary[]>([]);
  const [policy, setPolicy] = useState<MethodologyPolicy>({
    allowed_methodology_ids: null,
    default_methodology_id: null,
    department_overrides: {},
    enforce_published_only: true,
  });
  const [impact, setImpact] = useState<ImpactAnalysis | null>(null);
  const [selectedMethodology, setSelectedMethodology] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [policyDirty, setPolicyDirty] = useState(false);
  const [newDeptName, setNewDeptName] = useState('');
  const [restrictMethodologies, setRestrictMethodologies] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [methResponse, policyResponse] = await Promise.all([
        apiFetch<{ methodologies: MethodologySummary[] }>('/api/methodology/tenant/list'),
        apiFetch<MethodologyPolicy & { tenant_id: string }>('/api/methodology/policy'),
      ]);
      setMethodologies(methResponse.methodologies || []);
      const { tenant_id: _tid, ...policyData } = policyResponse;
      setPolicy(policyData);
      setRestrictMethodologies(policyData.allowed_methodology_ids !== null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load methodology settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handlePublish = useCallback(async (methodologyId: string) => {
    try {
      await apiFetch(`/api/methodology/tenant/${methodologyId}/publish`, { method: 'POST' });
      setSuccessMessage(`Methodology '${methodologyId}' published successfully.`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish methodology');
    }
  }, [loadData]);

  const handleDeprecate = useCallback(async (methodologyId: string) => {
    try {
      await apiFetch(`/api/methodology/tenant/${methodologyId}/deprecate`, { method: 'POST' });
      setSuccessMessage(`Methodology '${methodologyId}' deprecated.`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deprecate methodology');
    }
  }, [loadData]);

  const handleCheckImpact = useCallback(async (methodologyId: string) => {
    setSelectedMethodology(methodologyId);
    try {
      const result = await apiFetch<ImpactAnalysis>(`/api/methodology/tenant/${methodologyId}/impact`);
      setImpact(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check impact');
    }
  }, []);

  const handleSavePolicy = useCallback(async () => {
    setError(null);
    try {
      const payload = {
        ...policy,
        allowed_methodology_ids: restrictMethodologies ? (policy.allowed_methodology_ids || []) : null,
      };
      await apiFetch('/api/methodology/policy', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setSuccessMessage('Organisation methodology policy saved.');
      setPolicyDirty(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save policy');
    }
  }, [policy, restrictMethodologies, loadData]);

  const toggleAllowed = useCallback((methodologyId: string) => {
    setPolicy((prev) => {
      const current = prev.allowed_methodology_ids || [];
      const next = current.includes(methodologyId)
        ? current.filter((id) => id !== methodologyId)
        : [...current, methodologyId];
      return { ...prev, allowed_methodology_ids: next };
    });
    setPolicyDirty(true);
  }, []);

  const setDefault = useCallback((methodologyId: string | null) => {
    setPolicy((prev) => ({ ...prev, default_methodology_id: methodologyId }));
    setPolicyDirty(true);
  }, []);

  const addDepartmentOverride = useCallback(() => {
    if (!newDeptName.trim()) return;
    setPolicy((prev) => ({
      ...prev,
      department_overrides: {
        ...prev.department_overrides,
        [newDeptName.trim()]: { allowed_methodology_ids: [] },
      },
    }));
    setNewDeptName('');
    setPolicyDirty(true);
  }, [newDeptName]);

  const removeDepartmentOverride = useCallback((dept: string) => {
    setPolicy((prev) => {
      const next = { ...prev.department_overrides };
      delete next[dept];
      return { ...prev, department_overrides: next };
    });
    setPolicyDirty(true);
  }, []);

  const toggleDeptAllowed = useCallback((dept: string, methodologyId: string) => {
    setPolicy((prev) => {
      const deptPolicy = prev.department_overrides[dept] || {};
      const current = deptPolicy.allowed_methodology_ids || [];
      const next = current.includes(methodologyId)
        ? current.filter((id) => id !== methodologyId)
        : [...current, methodologyId];
      return {
        ...prev,
        department_overrides: {
          ...prev.department_overrides,
          [dept]: { ...deptPolicy, allowed_methodology_ids: next },
        },
      };
    });
    setPolicyDirty(true);
  }, []);

  const allMethodologyIds = methodologies.map((m) => m.methodology_id);

  return (
    <div className={styles.container} style={{ maxWidth: 960 }}>
      <h1 className={styles.pageTitle}>Organisation Methodology Settings</h1>
      <p className={styles.subtitle}>
        Configure which methodologies are available, set defaults, and manage department-level policies.
      </p>

      {error && <div className={styles.error}>{error}</div>}
      {successMessage && (
        <div style={{ padding: '0.5rem 1rem', marginBottom: '1rem', background: 'rgba(34,197,94,0.15)', borderRadius: 6, color: 'var(--color-success, #22c55e)' }}>
          {successMessage}
          <button onClick={() => setSuccessMessage(null)} style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>Dismiss</button>
        </div>
      )}

      {/* Methodology registry */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 className={styles.sectionTitle}>Methodology Registry</h2>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border, #333)', textAlign: 'left' }}>
                <th style={{ padding: '0.5rem' }}>Name</th>
                <th style={{ padding: '0.5rem' }}>Type</th>
                <th style={{ padding: '0.5rem' }}>Version</th>
                <th style={{ padding: '0.5rem' }}>Status</th>
                <th style={{ padding: '0.5rem' }}>Source</th>
                <th style={{ padding: '0.5rem' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {methodologies.map((m) => (
                <tr key={m.methodology_id} style={{ borderBottom: '1px solid var(--color-border, #222)' }}>
                  <td style={{ padding: '0.5rem' }}>
                    <strong>{m.name}</strong>
                    {m.is_default && <span style={{ marginLeft: 6, fontSize: '0.7rem', color: 'var(--color-accent, #FF6B35)' }}>DEFAULT</span>}
                    {m.description && <div style={{ fontSize: '0.75rem', color: 'var(--color-muted, #999)', marginTop: 2 }}>{m.description}</div>}
                  </td>
                  <td style={{ padding: '0.5rem' }}>{m.type}</td>
                  <td style={{ padding: '0.5rem' }}>v{m.version}</td>
                  <td style={{ padding: '0.5rem' }}><StatusBadge status={m.status} /></td>
                  <td style={{ padding: '0.5rem' }}>{m.source === 'builtin' ? 'Built-in' : 'Custom'}</td>
                  <td style={{ padding: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {m.status === 'draft' && (
                        <button className={styles.button} onClick={() => handlePublish(m.methodology_id)}>Publish</button>
                      )}
                      {m.status === 'published' && !m.is_builtin && (
                        <button className={styles.button} onClick={() => handleDeprecate(m.methodology_id)}>Deprecate</button>
                      )}
                      <button className={styles.buttonSecondary} onClick={() => handleCheckImpact(m.methodology_id)}>Check Impact</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Impact analysis panel */}
      {impact && selectedMethodology && (
        <section style={{ marginBottom: '2rem', padding: '1rem', background: 'var(--color-surface, #1a1a2e)', borderRadius: 8 }}>
          <h3>Change Impact: {selectedMethodology}</h3>
          <p style={{ color: impact.affected_workspace_count > 0 ? 'var(--color-warning, #eab308)' : 'var(--color-success, #22c55e)' }}>
            {impact.warning}
          </p>
          {impact.affected_workspaces.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '0.5rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border, #333)', textAlign: 'left', fontSize: '0.8rem' }}>
                  <th style={{ padding: '0.25rem 0.5rem' }}>Workspace</th>
                  <th style={{ padding: '0.25rem 0.5rem' }}>Project</th>
                  <th style={{ padding: '0.25rem 0.5rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {impact.affected_workspaces.map((ws) => (
                  <tr key={ws.workspace_id} style={{ fontSize: '0.8rem' }}>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{ws.workspace_id}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{ws.project_id}</td>
                    <td style={{ padding: '0.25rem 0.5rem' }}>{ws.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button className={styles.buttonSecondary} onClick={() => { setImpact(null); setSelectedMethodology(null); }} style={{ marginTop: 8 }}>Close</button>
        </section>
      )}

      {/* Organisation policy */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 className={styles.sectionTitle}>Organisation Policy</h2>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <input
              type="checkbox"
              checked={restrictMethodologies}
              onChange={(e) => { setRestrictMethodologies(e.target.checked); setPolicyDirty(true); }}
            />
            Restrict which methodologies can be used
          </label>

          {restrictMethodologies && (
            <div style={{ marginLeft: '1.5rem', marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-muted, #999)', marginBottom: 8 }}>
                Select the methodologies allowed for this organisation:
              </p>
              {allMethodologyIds.map((id) => (
                <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <input
                    type="checkbox"
                    checked={(policy.allowed_methodology_ids || []).includes(id)}
                    onChange={() => toggleAllowed(id)}
                  />
                  {id}
                </label>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Default Methodology</label>
          <select
            value={policy.default_methodology_id || ''}
            onChange={(e) => setDefault(e.target.value || null)}
            style={{ padding: '0.4rem', borderRadius: 4, background: 'var(--color-surface, #1a1a2e)', color: 'inherit', border: '1px solid var(--color-border, #333)' }}
          >
            <option value="">None (user selects)</option>
            {allMethodologyIds.map((id) => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox"
              checked={policy.enforce_published_only}
              onChange={(e) => { setPolicy((p) => ({ ...p, enforce_published_only: e.target.checked })); setPolicyDirty(true); }}
            />
            Only allow published methodologies for new workspaces
          </label>
        </div>

        {/* Department overrides */}
        <div style={{ marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1rem', marginBottom: 8 }}>Department-Level Overrides</h3>
          {Object.entries(policy.department_overrides).map(([dept, deptPolicy]) => (
            <div key={dept} style={{ padding: '0.5rem', marginBottom: 8, background: 'var(--color-surface, #1a1a2e)', borderRadius: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <strong>{dept}</strong>
                <button className={styles.buttonSecondary} onClick={() => removeDepartmentOverride(dept)} style={{ fontSize: '0.75rem' }}>Remove</button>
              </div>
              <div style={{ marginLeft: '0.5rem' }}>
                {allMethodologyIds.map((id) => (
                  <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2, fontSize: '0.85rem' }}>
                    <input
                      type="checkbox"
                      checked={(deptPolicy.allowed_methodology_ids || []).includes(id)}
                      onChange={() => toggleDeptAllowed(dept, id)}
                    />
                    {id}
                  </label>
                ))}
              </div>
            </div>
          ))}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Department name"
              value={newDeptName}
              onChange={(e) => setNewDeptName(e.target.value)}
              style={{ padding: '0.4rem', borderRadius: 4, background: 'var(--color-surface, #1a1a2e)', color: 'inherit', border: '1px solid var(--color-border, #333)' }}
            />
            <button className={styles.button} onClick={addDepartmentOverride}>Add Department</button>
          </div>
        </div>

        <button className={styles.button} onClick={handleSavePolicy} disabled={!policyDirty} style={{ opacity: policyDirty ? 1 : 0.5 }}>
          Save Policy
        </button>
      </section>
    </div>
  );
}
