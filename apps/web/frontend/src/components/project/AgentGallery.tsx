import { useEffect, useMemo, useState } from 'react';
import type { AgentConfig } from '@/store/agentConfig';
import { getMockAgents } from '@/store/agentConfig';
import styles from './AgentGallery.module.css';

interface AgentGalleryProps {
  projectId: string;
}

export function AgentGallery({ projectId }: AgentGalleryProps) {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadAgents = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/projects/${projectId}/agents`);
        if (!response.ok) {
          throw new Error(`Failed to fetch agents: ${response.statusText}`);
        }
        const data = (await response.json()) as AgentConfig[];
        if (isActive) {
          setAgents(data);
          setLoading(false);
        }
      } catch (fetchError) {
        if (isActive) {
          const message = fetchError instanceof Error ? fetchError.message : 'Unknown error';
          setError(message);
          setAgents(getMockAgents());
          setLoading(false);
        }
      }
    };

    loadAgents();

    return () => {
      isActive = false;
    };
  }, [projectId]);

  const enabledCount = useMemo(() => agents.filter((agent) => agent.enabled).length, [agents]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading agents...</div>
      </div>
    );
  }

  if (error && agents.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Error loading agents: {error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Agent Gallery</h2>
        <p className={styles.subtitle}>Project-scoped AI agents and their configuration status.</p>
      </div>

      <div className={styles.statusRow}>
        <span>
          {enabledCount} of {agents.length} agents enabled
        </span>
        {error ? <span>Using fallback data</span> : null}
      </div>

      <div className={styles.list}>
        {agents.map((agent) => (
          <div key={agent.agent_id} className={styles.card}>
            <div className={styles.cardHeader}>
              <h3 className={styles.cardTitle}>{agent.name}</h3>
              <span className={`${styles.badge} ${agent.enabled ? styles.enabled : styles.disabled}`}>
                {agent.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className={styles.cardDescription}>{agent.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AgentGallery;
