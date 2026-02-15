import type { CanvasComponentProps } from '../../types/canvas';
import type { ApprovalContent } from '../../types/artifact';
import styles from './ApprovalCanvas.module.css';

export interface ApprovalCanvasProps extends CanvasComponentProps<ApprovalContent> {}

export function ApprovalCanvas({ artifact, onChange, readOnly = false }: ApprovalCanvasProps) {
  const decide = (status: 'approved' | 'rejected') => {
    if (readOnly) return;
    onChange?.({
      ...artifact.content,
      status,
      history: [
        ...artifact.content.history,
        { id: `hist-${Date.now()}`, action: status === 'approved' ? 'approve' : 'reject', actor: 'Current User', timestamp: new Date().toISOString() },
      ],
    });
  };

  return (
    <div className={styles.wrap}>
      <h3>Status: {artifact.content.status}</h3>
      <section>
        <h4>Evidence</h4>
        <ul>{artifact.content.evidence.map((item, i)=><li key={i}>{item}</li>)}</ul>
      </section>
      {!readOnly && (
        <div className={styles.actions}>
          <button onClick={() => decide('approved')}>Approve</button>
          <button onClick={() => decide('rejected')}>Reject</button>
        </div>
      )}
      <section>
        <h4>History</h4>
        <ul>{artifact.content.history.map((entry)=><li key={entry.id}>{entry.action} by {entry.actor}</li>)}</ul>
      </section>
    </div>
  );
}
