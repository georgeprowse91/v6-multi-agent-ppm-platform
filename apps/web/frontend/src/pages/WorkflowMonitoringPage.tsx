import { useEffect, useState } from 'react';
import { useRealtimeStore } from '@/store/realtime/useRealtimeStore';
import styles from './WorkflowMonitoringPage.module.css';

const API_BASE = '/v1';

interface WorkflowInstance {
  run_id: string;
  workflow_id: string;
  status: string;
  current_step_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface WorkflowEvent {
  event_id: string;
  step_id?: string | null;
  status: string;
  message: string;
  created_at: string;
}

const samplePayload = {
  charter_id: 'charter-2026-001',
  requester: 'project-manager',
  project_id: 'project-alpha',
  description: 'Publish charter for Project Alpha',
  requires_approval: true,
};

export function WorkflowMonitoringPage() {
  const [instances, setInstances] = useState<WorkflowInstance[]>([]);
  const [selectedInstance, setSelectedInstance] =
    useState<WorkflowInstance | null>(null);
  const [timeline, setTimeline] = useState<WorkflowEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'open' | 'error'>('connecting');
  const [lastEventAt, setLastEventAt] = useState<string | null>(null);
  const realtimeConnected = useRealtimeStore((state) => state.connected);
  const realtimeWorkflowUpdates = useRealtimeStore((state) => state.workflowUpdates);

  const fetchInstances = async (options?: { silent?: boolean }) => {
    if (!options?.silent) {
      setLoading(true);
    }
    try {
      const response = await fetch(`${API_BASE}/workflows/instances`);
      const data = await response.json();
      setInstances(data);
    } catch (error) {
      console.error('Failed to fetch workflow instances', error);
    } finally {
      if (!options?.silent) {
        setLoading(false);
      }
    }
  };

  const fetchTimeline = async (runId: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/workflows/instances/${runId}/timeline`
      );
      const data = await response.json();
      setTimeline(data);
    } catch (error) {
      console.error('Failed to fetch timeline', error);
    }
  };

  const startSampleWorkflow = async () => {
    try {
      await fetch(`${API_BASE}/workflows/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: 'publish-charter',
          payload: samplePayload,
          actor: { id: 'project-manager', type: 'user' },
        }),
      });
      await fetchInstances();
    } catch (error) {
      console.error('Failed to start workflow', error);
    }
  };

  useEffect(() => {
    fetchInstances();
  }, []);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let pollInterval: number | null = null;

    const startPolling = () => {
      if (pollInterval) return;
      pollInterval = window.setInterval(() => {
        fetchInstances({ silent: true });
        if (selectedInstance) {
          fetchTimeline(selectedInstance.run_id);
        }
      }, 15000);
    };

    const stopPolling = () => {
      if (pollInterval) {
        window.clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    try {
      eventSource = new EventSource(`${API_BASE}/workflows/stream`);
      eventSource.onopen = () => {
        setStreamStatus('open');
        stopPolling();
      };
      eventSource.onerror = () => {
        setStreamStatus('error');
        eventSource?.close();
        startPolling();
      };
      eventSource.onmessage = (event) => {
        setLastEventAt(new Date().toLocaleTimeString());
        try {
          const payload = JSON.parse(event.data);
          if (payload.instances) {
            setInstances(payload.instances);
          } else if (payload.instance) {
            setInstances((prev) => {
              const next = prev.filter((item) => item.run_id !== payload.instance.run_id);
              return [payload.instance, ...next];
            });
          } else if (payload.event && payload.event.run_id && selectedInstance?.run_id === payload.event.run_id) {
            setTimeline((prev) => [payload.event, ...prev].slice(0, 50));
          } else {
            fetchInstances({ silent: true });
          }
        } catch {
          fetchInstances({ silent: true });
        }
      };
    } catch (error) {
      console.error('Failed to open workflow stream', error);
      setStreamStatus('error');
      startPolling();
    }

    return () => {
      eventSource?.close();
      stopPolling();
    };
  }, [selectedInstance]);

  useEffect(() => {
    if (selectedInstance) {
      fetchTimeline(selectedInstance.run_id);
    }
  }, [selectedInstance]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerRow}>
          <div>
            <h1>Workflow Monitoring</h1>
            <p>
              Track workflow instances and review their execution timelines in real
              time.
            </p>
          </div>
          <div className={styles.streamStatus}>
            <span
              className={`${styles.streamDot} ${
                streamStatus === 'open'
                  ? styles.streamLive
                  : streamStatus === 'connecting'
                  ? styles.streamConnecting
                  : styles.streamError
              }`}
              aria-hidden="true"
            ></span>
            <div>
              <div className={styles.streamLabel}>
                {streamStatus === 'open'
                  ? 'Live updates'
                  : streamStatus === 'connecting'
                  ? 'Connecting…'
                  : 'Realtime unavailable'}
              </div>
              <div className={styles.streamMeta}>
                {realtimeConnected
                  ? `Realtime coedit channel connected · ${realtimeWorkflowUpdates.length} workflow update(s)`
                  : lastEventAt
                  ? `Last event at ${lastEventAt}`
                  : 'Awaiting events'}
              </div>
            </div>
          </div>
        </div>
        <button className={styles.primaryButton} onClick={startSampleWorkflow}>
          Start “Publish Charter” workflow
        </button>
      </header>

      <div className={styles.layout}>
        <section className={styles.listSection}>
          <div className={styles.sectionHeader}>
            <h2>Instances</h2>
            <button onClick={() => { void fetchInstances(); }} className={styles.secondaryButton}>
              Refresh
            </button>
          </div>
          {loading && <div className={styles.emptyState}>Loading...</div>}
          {!loading && instances.length === 0 && (
            <div className={styles.emptyState}>
              No workflow instances yet. Start the sample workflow to populate
              the list.
            </div>
          )}
          <ul className={styles.instanceList}>
            {instances.map((instance) => (
              <li
                key={instance.run_id}
                className={`${styles.instanceCard} ${
                  selectedInstance?.run_id === instance.run_id
                    ? styles.activeCard
                    : ''
                }`}
                onClick={() => setSelectedInstance(instance)}
              >
                <div>
                  <h3>{instance.workflow_id}</h3>
                  <p>Run ID: {instance.run_id}</p>
                </div>
                <div className={styles.instanceMeta}>
                  <span className={styles.statusBadge}>{instance.status}</span>
                  <span>
                    Step: {instance.current_step_id ?? 'completed'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <aside className={styles.timelineSection}>
          <h2>Timeline</h2>
          {!selectedInstance && (
            <div className={styles.emptyState}>
              Select a workflow instance to view its timeline.
            </div>
          )}
          {selectedInstance && (
            <>
              <div className={styles.timelineHeader}>
                <h3>{selectedInstance.workflow_id}</h3>
                <p>{selectedInstance.run_id}</p>
              </div>
              <ul className={styles.timelineList}>
                {timeline.length === 0 && (
                  <li className={styles.emptyState}>No events recorded yet.</li>
                )}
                {timeline.map((event) => (
                  <li key={event.event_id} className={styles.timelineItem}>
                    <div>
                      <strong>{event.status}</strong>
                      <span>{event.created_at}</span>
                    </div>
                    <p>{event.message}</p>
                    {event.step_id && (
                      <span className={styles.stepTag}>{event.step_id}</span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

export default WorkflowMonitoringPage;
