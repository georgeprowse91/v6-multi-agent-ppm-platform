import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import styles from './ApprovalsPage.module.css';

const API_BASE = '/v1';
const DEFAULT_APPROVER = 'dev-user';

interface ApprovalSummary {
  approval_id: string;
  run_id: string;
  step_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: {
    request_type?: string;
    request_id?: string;
    approvers?: string[];
    deadline?: string;
    details?: Record<string, string>;
  };
}

interface ApprovalDetail extends ApprovalSummary {
  decision?: string | null;
  approver_id?: string | null;
  comments?: string | null;
  audit_trail: Array<{
    action: string;
    timestamp?: string;
    actor?: string;
    details?: Record<string, unknown>;
  }>;
}

export function ApprovalsPage() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project');
  const [approvals, setApprovals] = useState<ApprovalSummary[]>([]);
  const [selectedApproval, setSelectedApproval] =
    useState<ApprovalDetail | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        status: 'pending',
        approver_id: DEFAULT_APPROVER,
      });
      if (projectId) {
        params.set('project_id', projectId);
      }
      const response = await fetch(`${API_BASE}/workflows/approvals?${params.toString()}`);
      const data = await response.json();
      setApprovals(data);
      if (data.length === 0) {
        setSelectedApproval(null);
      }
    } catch (error) {
      console.error('Failed to fetch approvals', error);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const fetchApprovalDetail = async (approvalId: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/workflows/approvals/${approvalId}`
      );
      const detail = await response.json();
      setSelectedApproval(detail);
    } catch (error) {
      console.error('Failed to fetch approval detail', error);
    }
  };

  const submitDecision = async (approvalId: string, decision: string) => {
    try {
      await fetch(`${API_BASE}/workflows/approvals/${approvalId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          approver_id: DEFAULT_APPROVER,
          comments: comments[approvalId] || '',
        }),
      });
      await fetchApprovals();
      if (selectedApproval?.approval_id === approvalId) {
        await fetchApprovalDetail(approvalId);
      }
    } catch (error) {
      console.error('Failed to submit decision', error);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>My Approvals</h1>
        <p>
          Pending approvals assigned to <strong>{DEFAULT_APPROVER}</strong>
          {projectId ? (
            <> for project <strong>{projectId}</strong></>
          ) : null}.
        </p>
      </header>

      <div className={styles.layout}>
        <section className={styles.listSection}>
          <div className={styles.sectionHeader}>
            <h2>Pending approvals</h2>
            <button onClick={fetchApprovals} className={styles.refreshButton}>
              Refresh
            </button>
          </div>

          {loading && <div className={styles.emptyState}>Loading...</div>}
          {!loading && approvals.length === 0 && (
            <div className={styles.emptyState}>
              No approvals awaiting your decision.
            </div>
          )}
          <ul className={styles.cardList}>
            {approvals.map((approval) => (
              <li key={approval.approval_id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <div>
                    <h3>
                      {approval.metadata?.details?.description ??
                        approval.metadata?.request_type ??
                        'Approval Request'}
                    </h3>
                    <p>
                      Workflow run {approval.run_id} · Step{' '}
                      {approval.step_id}
                    </p>
                  </div>
                  <span className={styles.badge}>{approval.status}</span>
                </div>
                <div className={styles.metaRow}>
                  <span>Request ID: {approval.metadata?.request_id}</span>
                  <span>
                    Deadline: {approval.metadata?.deadline ?? 'Not set'}
                  </span>
                </div>
                <textarea
                  className={styles.commentBox}
                  placeholder="Add a comment (optional)"
                  value={comments[approval.approval_id] || ''}
                  onChange={(event) =>
                    setComments((prev) => ({
                      ...prev,
                      [approval.approval_id]: event.target.value,
                    }))
                  }
                />
                <div className={styles.cardActions}>
                  <button
                    className={styles.secondaryButton}
                    onClick={() => fetchApprovalDetail(approval.approval_id)}
                  >
                    View details
                  </button>
                  <div className={styles.actionGroup}>
                    <button
                      className={styles.rejectButton}
                      onClick={() =>
                        submitDecision(approval.approval_id, 'rejected')
                      }
                    >
                      Reject
                    </button>
                    <button
                      className={styles.approveButton}
                      onClick={() =>
                        submitDecision(approval.approval_id, 'approved')
                      }
                    >
                      Approve
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <aside className={styles.detailSection}>
          <h2>Approval details</h2>
          {!selectedApproval && (
            <div className={styles.emptyState}>
              Select an approval to see the audit trail.
            </div>
          )}
          {selectedApproval && (
            <div className={styles.detailCard}>
              <h3>{selectedApproval.metadata?.request_type}</h3>
              <p className={styles.detailSubtitle}>
                {selectedApproval.metadata?.details?.description ??
                  selectedApproval.metadata?.request_id}
              </p>
              <div className={styles.detailMeta}>
                <div>
                  <span>Status</span>
                  <strong>{selectedApproval.status}</strong>
                </div>
                <div>
                  <span>Deadline</span>
                  <strong>{selectedApproval.metadata?.deadline ?? 'N/A'}</strong>
                </div>
                <div>
                  <span>Approvers</span>
                  <strong>
                    {selectedApproval.metadata?.approvers?.join(', ') ?? 'N/A'}
                  </strong>
                </div>
              </div>
              <h4>Audit trail</h4>
              <ul className={styles.auditList}>
                {selectedApproval.audit_trail.length === 0 && (
                  <li className={styles.auditItem}>No audit events yet.</li>
                )}
                {selectedApproval.audit_trail.map((entry, index) => (
                  <li key={`${entry.action}-${index}`} className={styles.auditItem}>
                    <div>
                      <strong>{entry.action}</strong>
                      <span>{entry.timestamp ?? 'Pending'}</span>
                    </div>
                    <p>{entry.actor ?? 'system'}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
