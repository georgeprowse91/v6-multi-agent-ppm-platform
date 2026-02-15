import { useState } from 'react';
import type { MethodologyActivity } from '@/store/methodology';
import styles from './MethodologyMapCanvas.module.css';

interface ReviewItem {
  approval_id: string;
  requested_event: string;
  requested_at: string;
  notes?: string;
}

interface ActivityDetailPanelProps {
  activity: MethodologyActivity;
  stageLabel: string;
  isLocked: boolean;
  missingPrerequisites: string[];
  runtimeActionsAvailable: string[];
  reviewQueue: ReviewItem[];
  onLifecycleAction: (event: 'generate' | 'update' | 'review' | 'approve' | 'publish') => void;
  onReviewDecision: (approvalId: string, decision: 'approve' | 'reject' | 'modify', notes?: string) => void;
  actionsDisabled?: boolean;
}

const EVENTS: Array<'generate' | 'update' | 'review' | 'approve' | 'publish'> = ['generate', 'update', 'review', 'approve', 'publish'];

export function ActivityDetailPanel({
  activity,
  stageLabel,
  isLocked,
  missingPrerequisites,
  runtimeActionsAvailable,
  reviewQueue,
  onLifecycleAction,
  onReviewDecision,
  actionsDisabled = false,
}: ActivityDetailPanelProps) {
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});

  return (
    <section className={styles.canvas}>
      <h2>{activity.name}</h2>
      <p><strong>Stage:</strong> {stageLabel}</p>
      <p><strong>Status:</strong> {activity.status.replace('_', ' ')}</p>
      <p>{activity.description || 'No description available.'}</p>
      {missingPrerequisites.length > 0 && (
        <p><strong>Missing prerequisites:</strong> {missingPrerequisites.join(', ')}</p>
      )}
      {isLocked && <p>This activity is currently locked.</p>}
      <div className={styles.monitoringRow}>
        {EVENTS.filter((event) => runtimeActionsAvailable.includes(event)).map((event) => (
          <button key={event} type="button" className={styles.card} disabled={actionsDisabled} onClick={() => onLifecycleAction(event)}>
            {event}
          </button>
        ))}
      </div>
      <h3>Approvals inbox</h3>
      {reviewQueue.length === 0 && <p>No pending approvals.</p>}
      {reviewQueue.map((item) => (
        <div key={item.approval_id} className={styles.card}>
          <p><strong>{item.requested_event}</strong> · {new Date(item.requested_at).toLocaleString()}</p>
          <p>{item.notes ?? 'No notes provided.'}</p>
          <textarea
            value={decisionNotes[item.approval_id] ?? ''}
            onChange={(event) => setDecisionNotes((prev) => ({ ...prev, [item.approval_id]: event.target.value }))}
            placeholder="Decision notes"
          />
          <div className={styles.monitoringRow}>
            <button type="button" onClick={() => onReviewDecision(item.approval_id, 'approve', decisionNotes[item.approval_id])}>Approve</button>
            <button type="button" onClick={() => onReviewDecision(item.approval_id, 'reject', decisionNotes[item.approval_id])}>Reject</button>
            <button type="button" onClick={() => onReviewDecision(item.approval_id, 'modify', decisionNotes[item.approval_id])}>Modify</button>
          </div>
        </div>
      ))}
    </section>
  );
}
