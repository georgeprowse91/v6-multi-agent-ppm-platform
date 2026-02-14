import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useRequestState } from '@/hooks/useRequestState';
import { EmptyState } from '@/components/ui/EmptyState';
import { getErrorMessage, requestJson } from '@/services/apiClient';
import { useRealtimeStore } from '@/store/realtime/useRealtimeStore';
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
  const [selectedApproval, setSelectedApproval] = useState<ApprovalDetail | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const listRequest = useRequestState();
  const detailRequest = useRequestState();
  const { start: startList, succeed: succeedList, fail: failList } = listRequest;
  const { start: startDetail, succeed: succeedDetail, fail: failDetail } = detailRequest;
  const realtimeApprovals = useRealtimeStore((state) => state.approvalUpdates);

  const fetchApprovals = useCallback(async () => {
    startList();
    setBannerMessage(null);

    try {
      const params = new URLSearchParams({
        status: 'pending',
        approver_id: DEFAULT_APPROVER,
      });
      if (projectId) {
        params.set('project_id', projectId);
      }

      const data = await requestJson<ApprovalSummary[]>(
        `${API_BASE}/workflows/approvals?${params.toString()}`
      );

      setApprovals(data);
      if (data.length === 0) {
        setSelectedApproval(null);
      }
      succeedList();
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to load approvals.');
      failList(message);
      setApprovals([]);
    }
  }, [failList, projectId, startList, succeedList]);

  const fetchApprovalDetail = useCallback(
    async (approvalId: string) => {
      startDetail();
      setBannerMessage(null);

      try {
        const detail = await requestJson<ApprovalDetail>(
          `${API_BASE}/workflows/approvals/${approvalId}`
        );
        setSelectedApproval(detail);
        succeedDetail();
      } catch (error) {
        const message = getErrorMessage(error, 'Failed to load approval details.');
        failDetail(message);
      }
    },
    [failDetail, startDetail, succeedDetail]
  );

  const submitDecision = async (approvalId: string, decision: string) => {
    setIsSubmittingDecision(true);
    setBannerMessage(null);

    try {
      await requestJson<void>(`${API_BASE}/workflows/approvals/${approvalId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          approver_id: DEFAULT_APPROVER,
          comments: comments[approvalId] || '',
        }),
      });

      setBannerMessage(`Decision saved: ${decision}.`);
      await fetchApprovals();
      if (selectedApproval?.approval_id === approvalId) {
        await fetchApprovalDetail(approvalId);
      }
    } catch (error) {
      setBannerMessage(getErrorMessage(error, 'Failed to submit approval decision.'));
    } finally {
      setIsSubmittingDecision(false);
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
            <>
              {' '}
              for project <strong>{projectId}</strong>
            </>
          ) : null}
          .
        </p>
      </header>

      {bannerMessage && <div className={styles.infoBanner}>{bannerMessage}</div>}
      {realtimeApprovals.length > 0 && (
        <div className={styles.infoBanner}>
          Live updates: {realtimeApprovals.length} approval event(s) received.
        </div>
      )}

      <div className={styles.layout}>
        <section className={styles.listSection}>
          <div className={styles.sectionHeader}>
            <h2>Pending approvals</h2>
            <button onClick={fetchApprovals} className={styles.refreshButton}>
              Refresh
            </button>
          </div>

          {listRequest.isLoading && <div className={styles.emptyState}>Loading...</div>}
          {listRequest.isError && (
            <div className={styles.errorState}>
              <span>{listRequest.error}</span>
              <button onClick={fetchApprovals}>Retry</button>
            </div>
          )}
          {!listRequest.isLoading && !listRequest.isError && approvals.length === 0 && (
            <EmptyState
              icon="confirm"
              title="All caught up"
              description="No approvals need your attention right now."
            />
          )}
          {!listRequest.isLoading && !listRequest.isError && approvals.length > 0 && (
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
                        Workflow run {approval.run_id} · Step {approval.step_id}
                      </p>
                    </div>
                    <span className={styles.badge}>{approval.status}</span>
                  </div>
                  <div className={styles.metaRow}>
                    <span>Request ID: {approval.metadata?.request_id}</span>
                    <span>Deadline: {approval.metadata?.deadline ?? 'Not set'}</span>
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
                        onClick={() => submitDecision(approval.approval_id, 'rejected')}
                        disabled={isSubmittingDecision}
                      >
                        Reject
                      </button>
                      <button
                        className={styles.approveButton}
                        onClick={() => submitDecision(approval.approval_id, 'approved')}
                        disabled={isSubmittingDecision}
                      >
                        Approve
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className={styles.detailSection}>
          <h2>Approval details</h2>
          {detailRequest.isError && (
            <div className={styles.errorState}>
              <span>{detailRequest.error}</span>
              {selectedApproval && (
                <button onClick={() => fetchApprovalDetail(selectedApproval.approval_id)}>
                  Retry
                </button>
              )}
            </div>
          )}
          {!selectedApproval && !detailRequest.isLoading && (
            <div className={styles.emptyState}>Select an approval to see the audit trail.</div>
          )}
          {detailRequest.isLoading && <div className={styles.emptyState}>Loading details...</div>}
          {selectedApproval && !detailRequest.isLoading && (
            <div className={styles.detailCard}>
              <h3>{selectedApproval.metadata?.request_type}</h3>
              <p className={styles.detailSubtitle}>
                {selectedApproval.metadata?.details?.description ?? selectedApproval.metadata?.request_id}
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
                  <strong>{selectedApproval.metadata?.approvers?.join(', ') ?? 'N/A'}</strong>
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
