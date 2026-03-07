import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestJson, getErrorMessage } from '../services/apiClient';
import styles from './AgentMarketplacePage.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MarketplaceAgent {
  agent_id: string;
  display_name: string;
  version: string | null;
  description: string | null;
  category: string | null;
  author: { name: string; email?: string; url?: string } | null;
  tags: string[];
  icon: string | null;
  source: string;
  capabilities: string[];
  installed: boolean;
}

interface MarketplaceListResponse {
  agents: MarketplaceAgent[];
  total: number;
  builtin_count: number;
  marketplace_count: number;
}

interface CategoryEntry {
  value: string;
  label: string;
  count: number;
}

interface AgentDetail {
  agent_id: string;
  display_name: string;
  version: string | null;
  description: string | null;
  long_description: string | null;
  category: string | null;
  author: { name: string; email?: string; url?: string } | null;
  license: string | null;
  tags: string[];
  icon: string | null;
  source: string;
  capabilities: string[];
  permissions_required: string[];
  connectors_used: string[];
  schemas_used: string[];
  inputs: Array<{ name: string; type: string; required?: boolean; description?: string }>;
  outputs: Array<{ name: string; type: string; description?: string }>;
  parameters: Array<{ name: string; display_name: string; param_type: string; default_value: unknown; description?: string }>;
  runtime: { python_version?: string; memory_mb?: number; timeout_seconds?: number; sandbox?: boolean } | null;
  documentation_url: string | null;
  repository_url: string | null;
  published_at: string | null;
  installed: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_ICONS: Record<string, string> = {
  core: '⚙',
  portfolio: '📊',
  delivery: '🚀',
  operations: '🔧',
  platform: '🏗',
  governance: '🛡',
  analytics: '📈',
  integration: '🔗',
  custom: '🧩',
};

const SOURCE_LABELS: Record<string, string> = {
  builtin: 'Built-in',
  marketplace: 'Marketplace',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AgentMarketplacePage() {
  const navigate = useNavigate();

  // List state
  const [agents, setAgents] = useState<MarketplaceAgent[]>([]);
  const [categories, setCategories] = useState<CategoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [builtinCount, setBuiltinCount] = useState(0);
  const [marketplaceCount, setMarketplaceCount] = useState(0);

  // Detail drawer state
  const [selectedAgent, setSelectedAgent] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Register dialog state
  const [showRegister, setShowRegister] = useState(false);
  const [manifestJson, setManifestJson] = useState('');
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerSuccess, setRegisterSuccess] = useState<string | null>(null);

  // Fetch agents
  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedCategory !== 'all') params.set('category', selectedCategory);
      if (selectedSource !== 'all') params.set('source', selectedSource);
      if (search.trim()) params.set('search', search.trim());

      const [listRes, catRes] = await Promise.all([
        requestJson<MarketplaceListResponse>(`/v1/marketplace/agents?${params.toString()}`),
        requestJson<{ categories: CategoryEntry[] }>('/v1/marketplace/categories'),
      ]);

      setAgents(listRes.agents);
      setBuiltinCount(listRes.builtin_count);
      setMarketplaceCount(listRes.marketplace_count);
      setCategories(catRes.categories);
    } catch (fetchErr) {
      setError(getErrorMessage(fetchErr, 'Failed to load marketplace agents.'));
      // Fallback data for demo
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, [search, selectedCategory, selectedSource]);

  useEffect(() => {
    void fetchAgents();
  }, [fetchAgents]);

  // Open agent detail
  const openDetail = useCallback(async (agentId: string) => {
    setDetailLoading(true);
    try {
      const detail = await requestJson<AgentDetail>(`/v1/marketplace/agents/${agentId}`);
      setSelectedAgent(detail);
    } catch {
      setSelectedAgent(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Register new agent
  const handleRegister = useCallback(async () => {
    setRegisterError(null);
    setRegisterSuccess(null);
    try {
      const manifest = JSON.parse(manifestJson);
      const result = await requestJson<{ success: boolean; message: string }>(
        '/v1/marketplace/agents/register',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manifest }),
        },
      );
      setRegisterSuccess(result.message);
      setManifestJson('');
      void fetchAgents();
    } catch (regErr) {
      setRegisterError(getErrorMessage(regErr, 'Registration failed.'));
    }
  }, [manifestJson, fetchAgents]);

  // Remove agent
  const handleRemove = useCallback(async (agentId: string) => {
    try {
      await requestJson(`/v1/marketplace/agents/${agentId}`, { method: 'DELETE' });
      setSelectedAgent(null);
      void fetchAgents();
    } catch (rmErr) {
      setError(getErrorMessage(rmErr, 'Failed to remove agent.'));
    }
  }, [fetchAgents]);

  // Filtered display
  const displayAgents = agents;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <h1>Agent Marketplace</h1>
            <p className={styles.subtitle}>Browse, install, and manage AI agents for your PPM platform.</p>
          </div>
          <button
            type="button"
            className={styles.registerBtn}
            onClick={() => setShowRegister(!showRegister)}
          >
            {showRegister ? 'Close' : 'Register Agent'}
          </button>
        </div>

        <div className={styles.stats}>
          <span className={styles.statItem}>{builtinCount + marketplaceCount} total agents</span>
          <span className={styles.statDot} />
          <span className={styles.statItem}>{builtinCount} built-in</span>
          <span className={styles.statDot} />
          <span className={styles.statItem}>{marketplaceCount} marketplace</span>
        </div>
      </header>

      {/* Register Dialog */}
      {showRegister && (
        <div className={styles.registerPanel}>
          <h3>Register Custom Agent</h3>
          <p className={styles.registerHint}>Paste the agent manifest JSON to register a new third-party agent.</p>
          <textarea
            className={styles.manifestInput}
            placeholder='{"manifest_version": "1.0", "agent_id": "my-agent", ...}'
            value={manifestJson}
            onChange={(e) => setManifestJson(e.target.value)}
            rows={8}
          />
          <div className={styles.registerActions}>
            <button
              type="button"
              className={styles.submitBtn}
              onClick={handleRegister}
              disabled={!manifestJson.trim()}
            >
              Register
            </button>
            {registerError && <span className={styles.registerError}>{registerError}</span>}
            {registerSuccess && <span className={styles.registerSuccess}>{registerSuccess}</span>}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className={styles.filters}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Search agents by name, description, or tag..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className={styles.filterSelect}
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="all">All categories</option>
          {categories.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label} ({cat.count})
            </option>
          ))}
        </select>
        <select
          className={styles.filterSelect}
          value={selectedSource}
          onChange={(e) => setSelectedSource(e.target.value)}
        >
          <option value="all">All sources</option>
          <option value="builtin">Built-in</option>
          <option value="marketplace">Marketplace</option>
        </select>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {/* Agent Grid */}
      {loading ? (
        <div className={styles.loadingState}>Loading agents...</div>
      ) : displayAgents.length === 0 ? (
        <div className={styles.emptyState}>No agents found matching your criteria.</div>
      ) : (
        <div className={styles.grid}>
          {displayAgents.map((agent) => (
            <div
              key={agent.agent_id}
              className={styles.card}
              onClick={() => openDetail(agent.agent_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && openDetail(agent.agent_id)}
            >
              <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                  {CATEGORY_ICONS[agent.category || 'custom'] || '🧩'}
                </span>
                <div className={styles.cardMeta}>
                  <h3 className={styles.cardTitle}>{agent.display_name}</h3>
                  {agent.version && <span className={styles.cardVersion}>v{agent.version}</span>}
                </div>
                <span className={`${styles.sourceBadge} ${agent.source === 'marketplace' ? styles.sourceMarketplace : styles.sourceBuiltin}`}>
                  {SOURCE_LABELS[agent.source] || agent.source}
                </span>
              </div>
              <p className={styles.cardDescription}>{agent.description || 'No description available.'}</p>
              <div className={styles.cardFooter}>
                {agent.author && <span className={styles.cardAuthor}>{agent.author.name}</span>}
                {agent.category && (
                  <span className={styles.cardCategory}>{agent.category}</span>
                )}
              </div>
              {agent.tags.length > 0 && (
                <div className={styles.cardTags}>
                  {agent.tags.slice(0, 4).map((tag) => (
                    <span key={tag} className={styles.tag}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Detail Drawer */}
      {selectedAgent && (
        <div className={styles.drawerOverlay} onClick={() => setSelectedAgent(null)}>
          <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
            <div className={styles.drawerHeader}>
              <div>
                <h2>{selectedAgent.display_name}</h2>
                {selectedAgent.version && <span className={styles.cardVersion}>v{selectedAgent.version}</span>}
              </div>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setSelectedAgent(null)}
              >
                ✕
              </button>
            </div>

            <div className={styles.drawerBody}>
              <div className={styles.detailRow}>
                <span className={`${styles.sourceBadge} ${selectedAgent.source === 'marketplace' ? styles.sourceMarketplace : styles.sourceBuiltin}`}>
                  {SOURCE_LABELS[selectedAgent.source] || selectedAgent.source}
                </span>
                {selectedAgent.category && (
                  <span className={styles.cardCategory}>{selectedAgent.category}</span>
                )}
                {selectedAgent.license && (
                  <span className={styles.licenseBadge}>{selectedAgent.license}</span>
                )}
              </div>

              {selectedAgent.author && (
                <p className={styles.detailAuthor}>
                  By {selectedAgent.author.name}
                  {selectedAgent.author.url && (
                    <>
                      {' · '}
                      <a href={selectedAgent.author.url} target="_blank" rel="noopener noreferrer">
                        Website
                      </a>
                    </>
                  )}
                </p>
              )}

              <p className={styles.detailDescription}>{selectedAgent.description}</p>
              {selectedAgent.long_description && (
                <p className={styles.detailLong}>{selectedAgent.long_description}</p>
              )}

              {selectedAgent.capabilities.length > 0 && (
                <section className={styles.detailSection}>
                  <h4>Capabilities</h4>
                  <div className={styles.chipList}>
                    {selectedAgent.capabilities.map((cap) => (
                      <span key={cap} className={styles.chip}>{cap.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                </section>
              )}

              {selectedAgent.tags.length > 0 && (
                <section className={styles.detailSection}>
                  <h4>Tags</h4>
                  <div className={styles.chipList}>
                    {selectedAgent.tags.map((t) => (
                      <span key={t} className={styles.tag}>{t}</span>
                    ))}
                  </div>
                </section>
              )}

              {selectedAgent.permissions_required.length > 0 && (
                <section className={styles.detailSection}>
                  <h4>Permissions Required</h4>
                  <div className={styles.chipList}>
                    {selectedAgent.permissions_required.map((p) => (
                      <span key={p} className={styles.permChip}>{p}</span>
                    ))}
                  </div>
                </section>
              )}

              {selectedAgent.inputs.length > 0 && (
                <section className={styles.detailSection}>
                  <h4>Inputs</h4>
                  <table className={styles.ioTable}>
                    <thead><tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr></thead>
                    <tbody>
                      {selectedAgent.inputs.map((inp) => (
                        <tr key={inp.name}>
                          <td className={styles.mono}>{inp.name}</td>
                          <td>{inp.type}</td>
                          <td>{inp.required ? 'Yes' : 'No'}</td>
                          <td>{inp.description || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              {selectedAgent.outputs.length > 0 && (
                <section className={styles.detailSection}>
                  <h4>Outputs</h4>
                  <table className={styles.ioTable}>
                    <thead><tr><th>Name</th><th>Type</th><th>Description</th></tr></thead>
                    <tbody>
                      {selectedAgent.outputs.map((out) => (
                        <tr key={out.name}>
                          <td className={styles.mono}>{out.name}</td>
                          <td>{out.type}</td>
                          <td>{out.description || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              {selectedAgent.runtime && (
                <section className={styles.detailSection}>
                  <h4>Runtime Requirements</h4>
                  <div className={styles.runtimeGrid}>
                    <div className={styles.runtimeItem}>
                      <span className={styles.runtimeLabel}>Python</span>
                      <span>{selectedAgent.runtime.python_version || '>=3.11'}</span>
                    </div>
                    <div className={styles.runtimeItem}>
                      <span className={styles.runtimeLabel}>Memory</span>
                      <span>{selectedAgent.runtime.memory_mb || 256} MB</span>
                    </div>
                    <div className={styles.runtimeItem}>
                      <span className={styles.runtimeLabel}>Timeout</span>
                      <span>{selectedAgent.runtime.timeout_seconds || 60}s</span>
                    </div>
                    <div className={styles.runtimeItem}>
                      <span className={styles.runtimeLabel}>Sandbox</span>
                      <span>{selectedAgent.runtime.sandbox !== false ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </section>
              )}

              {(selectedAgent.documentation_url || selectedAgent.repository_url) && (
                <section className={styles.detailSection}>
                  <h4>Links</h4>
                  <div className={styles.linkList}>
                    {selectedAgent.documentation_url && (
                      <a href={selectedAgent.documentation_url} target="_blank" rel="noopener noreferrer">
                        Documentation
                      </a>
                    )}
                    {selectedAgent.repository_url && (
                      <a href={selectedAgent.repository_url} target="_blank" rel="noopener noreferrer">
                        Source Code
                      </a>
                    )}
                  </div>
                </section>
              )}

              <div className={styles.drawerActions}>
                <button
                  type="button"
                  className={styles.configBtn}
                  onClick={() => navigate(`/config/agents/${selectedAgent.agent_id}`)}
                >
                  Configure
                </button>
                {selectedAgent.source === 'marketplace' && (
                  <button
                    type="button"
                    className={styles.removeBtn}
                    onClick={() => handleRemove(selectedAgent.agent_id)}
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentMarketplacePage;
