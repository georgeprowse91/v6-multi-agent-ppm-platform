import { useEffect, useMemo, useState } from 'react';
import { useAppStore } from '@/store';
import styles from './MergeReviewPage.module.css';

const API_BASE = '/v1';
const DEFAULT_REVIEWER = 'merge-reviewer';

interface MergeRecord {
  record_id: string;
  source_system: string;
  summary: string;
  attributes: Record<string, string>;
  last_updated?: string | null;
}

interface MergePreview {
  summary: string;
  attributes: Record<string, string>;
}

interface MergeReviewCase {
  case_id: string;
  entity_type: string;
  status: 'pending' | 'approved' | 'rejected';
  similarity_score: number;
  rationale: string;
  primary_record: MergeRecord;
  duplicate_record: MergeRecord;
  merge_preview: MergePreview;
  created_at: string;
  updated_at: string;
}

export function MergeReviewPage() {
  const { featureFlags } = useAppStore();
  const [cases, setCases] = useState<MergeReviewCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewerId, setReviewerId] = useState(DEFAULT_REVIEWER);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCase = useMemo(
    () => cases.find((item) => item.case_id === selectedId) ?? cases[0] ?? null,
    [cases, selectedId]
  );

  const fetchCases = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/merge-review?status=pending`);
      if (!response.ok) {
        throw new Error('Unable to fetch merge review cases.');
      }
      const data = await response.json();
      setCases(data);
      setError(null);
      if (data.length > 0) {
        setSelectedId((prev) => prev ?? data[0].case_id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to fetch merge review cases.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const submitDecision = async (caseId: string, decision: 'approved' | 'rejected') => {
    try {
      const response = await fetch(`${API_BASE}/api/merge-review/${caseId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reviewer_id: reviewerId,
          comments: comments[caseId] || undefined,
        }),
      });
      if (!response.ok) {
        throw new Error('Unable to submit merge decision.');
      }
      await fetchCases();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to submit merge decision.';
      setError(message);
    }
  };

  useEffect(() => {
    if (featureFlags.duplicate_resolution) {
      fetchCases();
    }
  }, [featureFlags.duplicate_resolution]);

  if (!featureFlags.duplicate_resolution) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyState}>
          Duplicate resolution is currently disabled.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Merge review</h1>
          <p>Approve or reject duplicate merges with a preview of the proposed record.</p>
        </div>
        <button className={styles.refreshButton} onClick={fetchCases}>
          Refresh
        </button>
      </header>

      <div className={styles.reviewerRow}>
        <label>
          Reviewer ID
          <input
            type="text"
            value={reviewerId}
            onChange={(event) => setReviewerId(event.target.value)}
          />
        </label>
        <span className={styles.helperText}>
          Decisions are recorded in the audit log once submitted.
        </span>
      </div>

      {loading && <div className={styles.emptyState}>Loading merge review cases...</div>}
      {!loading && error && <div className={styles.errorState}>{error}</div>}
      {!loading && !error && cases.length === 0 && (
        <div className={styles.emptyState}>No pending merge reviews.</div>
      )}

      {!loading && !error && cases.length > 0 && (
        <div className={styles.layout}>
          <div className={styles.caseList}>
            {cases.map((item) => (
              <button
                key={item.case_id}
                className={`${styles.caseCard} ${
                  selectedCase?.case_id === item.case_id ? styles.active : ''
                }`}
                onClick={() => setSelectedId(item.case_id)}
              >
                <div>
                  <h2>{item.primary_record.summary}</h2>
                  <p className={styles.muted}>
                    {item.entity_type} · Similarity {item.similarity_score.toFixed(2)}
                  </p>
                </div>
                <span className={styles.badge}>{item.status}</span>
              </button>
            ))}
          </div>

          {selectedCase && (
            <section className={styles.previewPanel}>
              <div className={styles.previewHeader}>
                <div>
                  <h2>Preview merge</h2>
                  <p className={styles.muted}>{selectedCase.rationale}</p>
                </div>
                <div className={styles.previewMeta}>
                  <span>Case ID: {selectedCase.case_id}</span>
                  <span>Entity: {selectedCase.entity_type}</span>
                </div>
              </div>

              <div className={styles.previewGrid}>
                <div className={styles.previewColumn}>
                  <h3>Primary record</h3>
                  <p className={styles.muted}>
                    {selectedCase.primary_record.source_system}
                  </p>
                  <dl>
                    {Object.entries(selectedCase.primary_record.attributes).map(([key, value]) => (
                      <div key={key} className={styles.previewRow}>
                        <dt>{key.replace(/_/g, ' ')}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className={styles.previewColumn}>
                  <h3>Duplicate record</h3>
                  <p className={styles.muted}>
                    {selectedCase.duplicate_record.source_system}
                  </p>
                  <dl>
                    {Object.entries(selectedCase.duplicate_record.attributes).map(([key, value]) => (
                      <div key={key} className={styles.previewRow}>
                        <dt>{key.replace(/_/g, ' ')}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className={styles.previewColumn}>
                  <h3>Proposed merge</h3>
                  <p className={styles.muted}>{selectedCase.merge_preview.summary}</p>
                  <dl>
                    {Object.entries(selectedCase.merge_preview.attributes).map(([key, value]) => (
                      <div key={key} className={styles.previewRow}>
                        <dt>{key.replace(/_/g, ' ')}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>

              <textarea
                className={styles.commentBox}
                placeholder="Add review comments"
                value={comments[selectedCase.case_id] || ''}
                onChange={(event) =>
                  setComments((prev) => ({
                    ...prev,
                    [selectedCase.case_id]: event.target.value,
                  }))
                }
              />
              <div className={styles.actions}>
                <button
                  className={styles.rejectButton}
                  onClick={() => submitDecision(selectedCase.case_id, 'rejected')}
                >
                  Reject
                </button>
                <button
                  className={styles.approveButton}
                  onClick={() => submitDecision(selectedCase.case_id, 'approved')}
                >
                  Approve merge
                </button>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
