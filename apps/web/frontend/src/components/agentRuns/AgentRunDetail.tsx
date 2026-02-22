import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ProgressBadge } from './ProgressBadge';
import type { AgentRunRecord } from '@/types/agentRuns';
import { useAppStore } from '@/store';
import styles from './AgentRunDetail.module.css';

interface AgentRunDetailProps {
  run?: AgentRunRecord | null;
}

const formatTimestamp = (value?: string | null) => {
  if (!value) return 'Not available';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

const formatReason = (value?: string | null) => {
  if (!value) return 'Not available';
  return value;
};

const extractAuditIds = (metadata?: Record<string, unknown>): string[] => {
  if (!metadata) return [];
  const candidates = [
    'audit_event_id',
    'audit_event_ids',
    'audit_event',
    'audit_events',
    'audit_id',
    'audit_ids',
    'auditId',
    'auditIds',
  ];
  const collectIds = (value: unknown): string[] => {
    if (!value) return [];
    if (typeof value === 'string') return [value];
    if (Array.isArray(value)) return value.flatMap(collectIds).filter(Boolean);
    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      if (typeof record.id === 'string') return [record.id];
      if (typeof record.event_id === 'string') return [record.event_id];
    }
    return [];
  };
  const ids = candidates.flatMap((key) => collectIds(metadata[key]));
  return Array.from(new Set(ids));
};

const getProgress = (metadata?: Record<string, unknown>) => {
  if (!metadata) return null;
  const progress = metadata.progress ?? metadata.progress_percent ?? metadata.progressPercent;
  if (typeof progress === 'number') return progress;
  if (typeof progress === 'string') {
    const parsed = Number(progress);
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
};

type AllocationRecord = {
  request_id?: string;
  resource_id?: string;
  score?: number;
  effort?: number;
  rationale?: string[];
  scoring?: {
    weighted_score?: number;
    components?: Record<string, number>;
  };
};

type OptimizationPayload = {
  proposed_allocations?: AllocationRecord[];
  recommended_allocations?: AllocationRecord[];
  applied_allocations?: AllocationRecord[];
  approval?: Record<string, unknown>;
  approval_status?: string;
  constraints?: Record<string, unknown>;
  scoring?: Record<string, unknown>;
};

const extractOptimization = (metadata?: Record<string, unknown>) => {
  if (!metadata) return null;
  const candidate =
    metadata.resource_optimization ??
    metadata.resourceOptimization ??
    metadata.optimization ??
    metadata.resource_allocation ??
    metadata.resourceAllocation;
  if (!candidate || typeof candidate !== 'object') return null;
  return candidate as OptimizationPayload;
};

const normalizeAllocations = (value: unknown): AllocationRecord[] => {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => typeof item === 'object') as AllocationRecord[];
};

export function AgentRunDetail({ run }: AgentRunDetailProps) {
  const { featureFlags } = useAppStore();
  const rawMetadata = run?.data.metadata;
  const metadata = useMemo(() => rawMetadata ?? {}, [rawMetadata]);
  const auditIds = useMemo(() => extractAuditIds(rawMetadata), [rawMetadata]);
  const optimization = useMemo(() => extractOptimization(rawMetadata), [rawMetadata]);
  const recommendationAllocations = useMemo(
    () =>
      normalizeAllocations(
        optimization?.proposed_allocations ?? optimization?.recommended_allocations
      ),
    [optimization]
  );
  const appliedAllocations = useMemo(
    () => normalizeAllocations(optimization?.applied_allocations),
    [optimization]
  );
  const hasOptimization =
    recommendationAllocations.length > 0 || appliedAllocations.length > 0;
  const [allocationView, setAllocationView] = useState<'recommendations' | 'applied'>(
    'recommendations'
  );
  useEffect(() => {
    setAllocationView(recommendationAllocations.length ? 'recommendations' : 'applied');
  }, [recommendationAllocations.length, run?.data.id]);

  if (!run) {
    return <div className={styles.empty}>Select a run to see details.</div>;
  }

  const allocations =
    allocationView === 'applied' ? appliedAllocations : recommendationAllocations;
  const approvalStatusRaw =
    optimization?.approval?.status ??
    optimization?.approval_status ??
    metadata.approval_status ??
    metadata.approvalStatus;
  const approvalStatus =
    typeof approvalStatusRaw === 'string' ? approvalStatusRaw : 'unknown';
  const approvalApproved = approvalStatus === 'approved';
  const resourceOptimizationEnabled = featureFlags.resource_optimization === true;

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>{run.data.id}</h2>
          <p className={styles.subTitle}>Agent: {run.data.agent_id}</p>
        </div>
        <ProgressBadge status={run.data.status} progress={getProgress(metadata)} />
      </header>

      <div className={styles.section}>
        <h3>Timeline</h3>
        <dl className={styles.definition}>
          <dt>Created</dt>
          <dd>{formatTimestamp(run.data.created_at)}</dd>
          <dt>Started</dt>
          <dd>{formatTimestamp(run.data.started_at)}</dd>
          <dt>Completed</dt>
          <dd>{formatTimestamp(run.data.completed_at)}</dd>
          <dt>Delay reason</dt>
          <dd>{formatReason(run.data.delay_reason)}</dd>
          <dt>Completion reason</dt>
          <dd>{formatReason(run.data.completion_reason)}</dd>
          <dt>Updated</dt>
          <dd>{formatTimestamp(run.data.updated_at)}</dd>
        </dl>
      </div>

      <div className={styles.section}>
        <h3>Audit trail</h3>
        {auditIds.length ? (
          <div className={styles.linkList}>
            {auditIds.map((auditId) => (
              <Link
                key={auditId}
                className={styles.link}
                to={`/admin/audit?eventId=${encodeURIComponent(auditId)}`}
              >
                Audit event {auditId}
              </Link>
            ))}
          </div>
        ) : (
          <p className={styles.subTitle}>No audit identifiers were recorded for this run.</p>
        )}
      </div>

      {resourceOptimizationEnabled && hasOptimization && (
        <div className={styles.section}>
          <div className={styles.sectionHeaderRow}>
            <h3>Resource allocations</h3>
            <div className={styles.toggleGroup} role="tablist">
              <button
                type="button"
                className={`${styles.toggleButton} ${
                  allocationView === 'recommendations' ? styles.activeToggle : ''
                }`}
                onClick={() => setAllocationView('recommendations')}
                disabled={recommendationAllocations.length === 0}
                role="tab"
                aria-selected={allocationView === 'recommendations'}
              >
                Recommendations
              </button>
              <button
                type="button"
                className={`${styles.toggleButton} ${
                  allocationView === 'applied' ? styles.activeToggle : ''
                }`}
                onClick={() => setAllocationView('applied')}
                disabled={appliedAllocations.length === 0}
                role="tab"
                aria-selected={allocationView === 'applied'}
              >
                Applied
              </button>
            </div>
          </div>
          <div className={styles.approvalRow}>
            <span className={styles.approvalLabel}>Approval status:</span>
            <span
              className={`${styles.approvalBadge} ${
                approvalApproved ? styles.approved : styles.pending
              }`}
            >
              {approvalStatus}
            </span>
          </div>
          {allocations.length === 0 && (
            <p className={styles.subTitle}>No allocations available for this view.</p>
          )}
          {allocations.length > 0 && (
            <ul className={styles.allocationList}>
              {allocations.map((allocation, index) => (
                <li key={`${allocation.request_id ?? 'request'}-${index}`}>
                  <div className={styles.allocationHeader}>
                    <div>
                      <strong>{allocation.resource_id ?? 'Unassigned'}</strong>
                      <div className={styles.subTitle}>
                        Request {allocation.request_id ?? 'unknown'} · Effort{' '}
                        {allocation.effort ?? '—'}
                      </div>
                    </div>
                    <span className={styles.scoreBadge}>
                      Score {(allocation.scoring?.weighted_score ?? allocation.score ?? 0).toFixed(2)}
                    </span>
                  </div>
                  {allocation.rationale && allocation.rationale.length > 0 && (
                    <ul className={styles.rationaleList}>
                      {allocation.rationale.map((item, rationaleIndex) => (
                        <li key={`${allocation.resource_id}-${rationaleIndex}`}>{item}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
          <div className={styles.applyRow}>
            {!approvalApproved && (
              <span className={styles.subTitle}>
                Approval is required before applying recommendations.
              </span>
            )}
            <button
              type="button"
              className={styles.primaryButton}
              disabled={!approvalApproved || allocationView !== 'recommendations'}
            >
              Apply allocations
            </button>
          </div>
        </div>
      )}

      <div className={styles.section}>
        <h3>Metadata</h3>
        <pre className={styles.metadata}>{JSON.stringify(metadata, null, 2)}</pre>
      </div>
    </section>
  );
}
