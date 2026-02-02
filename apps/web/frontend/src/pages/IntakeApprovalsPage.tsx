import { useEffect, useState } from 'react';
import { hasPermission } from '@/auth/permissions';
import { useAppStore } from '@/store';
import styles from './IntakeApprovalsPage.module.css';

const API_BASE = '/v1';
const DEFAULT_REVIEWER = 'pm-reviewer';

interface IntakeRequest {
  request_id: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  sponsor: {
    name: string;
    department: string;
    email: string;
  };
  business_case: {
    summary: string;
    expected_benefits: string;
  };
  success_criteria: {
    metrics: string;
  };
  attachments: {
    summary: string;
  };
  reviewers: string[];
  decision?: {
    decision: 'approved' | 'rejected';
    reviewer_id: string;
    comments?: string | null;
    decided_at: string;
  } | null;
}

export function IntakeApprovalsPage() {
  const { session } = useAppStore();
  const [requests, setRequests] = useState<IntakeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewerId, setReviewerId] = useState(DEFAULT_REVIEWER);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const canApprove = hasPermission(session.user?.permissions, 'intake.approve');

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/intake?status=pending`);
      if (!response.ok) {
        throw new Error('Unable to fetch intake requests.');
      }
      const data = await response.json();
      setRequests(data);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to fetch intake requests.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const submitDecision = async (requestId: string, decision: 'approved' | 'rejected') => {
    if (!canApprove) {
      setError('You do not have permission to approve intake requests.');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/intake/${requestId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reviewer_id: reviewerId,
          comments: comments[requestId] || undefined,
        }),
      });
      if (!response.ok) {
        throw new Error('Unable to submit decision.');
      }
      await fetchRequests();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to submit decision.';
      setError(message);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Intake approvals</h1>
          <p>Review incoming portfolio intake submissions and record a decision.</p>
        </div>
        <button className={styles.refreshButton} onClick={fetchRequests}>
          Refresh
        </button>
      </header>

      {!canApprove && (
        <div className={styles.errorState}>
          You do not have permission to submit intake decisions.
        </div>
      )}

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
          Only reviewers listed on the request can submit a decision.
        </span>
      </div>

      {loading && <div className={styles.emptyState}>Loading intake requests...</div>}
      {!loading && error && <div className={styles.errorState}>{error}</div>}
      {!loading && !error && requests.length === 0 && (
        <div className={styles.emptyState}>No pending intake requests.</div>
      )}

      <div className={styles.cards}>
        {requests.map((request) => (
          <div key={request.request_id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2>{request.business_case.summary}</h2>
                <p className={styles.muted}>
                  Sponsor: {request.sponsor.name} · {request.sponsor.department}
                </p>
              </div>
              <span className={styles.badge}>{request.status}</span>
            </div>
            <div className={styles.cardBody}>
              <p>{request.business_case.expected_benefits}</p>
              <p className={styles.muted}>Success metrics: {request.success_criteria.metrics}</p>
              <p className={styles.muted}>Attachments: {request.attachments.summary}</p>
              <p className={styles.muted}>
                Reviewers: {request.reviewers.length ? request.reviewers.join(', ') : 'Unassigned'}
              </p>
            </div>
            <textarea
              className={styles.commentBox}
              placeholder="Add review comments"
              value={comments[request.request_id] || ''}
              onChange={(event) =>
                setComments((prev) => ({
                  ...prev,
                  [request.request_id]: event.target.value,
                }))
              }
            />
            <div className={styles.cardActions}>
              <button
                className={styles.rejectButton}
                onClick={() => submitDecision(request.request_id, 'rejected')}
                disabled={!canApprove}
              >
                Reject
              </button>
              <button
                className={styles.approveButton}
                onClick={() => submitDecision(request.request_id, 'approved')}
                disabled={!canApprove}
              >
                Approve
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
