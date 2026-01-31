import { useEffect, useRef } from 'react';
import { useCoeditStore } from '../../store/documents';
import styles from './CoeditEditor.module.css';

export interface CoeditEditorProps {
  sessionId: string;
  documentId: string;
  userId: string;
  userName?: string;
}

const getCursorPosition = (): number => {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return 0;
  }
  return selection.anchorOffset ?? 0;
};

export function CoeditEditor({
  sessionId,
  documentId,
  userId,
  userName,
}: CoeditEditorProps) {
  const editorRef = useRef<HTMLDivElement | null>(null);
  const {
    content,
    connected,
    participants,
    cursors,
    conflicts,
    error,
    connect,
    disconnect,
    sendContentUpdate,
    updateCursor,
  } = useCoeditStore();

  useEffect(() => {
    connect({ sessionId, documentId, userId, userName });
    return () => disconnect();
  }, [connect, disconnect, sessionId, documentId, userId, userName]);

  useEffect(() => {
    if (!editorRef.current) return;
    if (editorRef.current.innerHTML !== content) {
      editorRef.current.innerHTML = content;
    }
  }, [content]);

  const handleInput = () => {
    const nextContent = editorRef.current?.innerHTML ?? '';
    sendContentUpdate(nextContent);
  };

  const handleSelectionUpdate = () => {
    updateCursor({ position: getCursorPosition() });
  };

  return (
    <div className={styles.container}>
      <section className={styles.editorPane}>
        <div className={styles.statusRow}>
          <span>Collaborative editor</span>
          <span
            className={`${styles.connectionBadge} ${
              connected ? styles.connected : ''
            }`}
          >
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div
          ref={editorRef}
          className={styles.editor}
          contentEditable
          role="textbox"
          aria-label="Collaborative document editor"
          onInput={handleInput}
          onKeyUp={handleSelectionUpdate}
          onMouseUp={handleSelectionUpdate}
          suppressContentEditableWarning
        />
        {error && <div className={styles.error}>{error}</div>}
      </section>
      <aside className={styles.sidebar}>
        <h4>Collaborators</h4>
        <ul className={styles.participants}>
          {participants.length === 0 && <li>No active collaborators.</li>}
          {participants.map((participant) => (
            <li key={participant.userId} className={styles.participantItem}>
              <strong>{participant.userName}</strong>
              <span className={styles.cursorMeta}>
                Cursor: {cursors[participant.userId]?.position ?? 0}
              </span>
            </li>
          ))}
        </ul>
        <h4>Conflict log</h4>
        <div className={styles.conflicts}>
          {conflicts.length === 0
            ? 'No conflicts detected.'
            : `${conflicts.length} conflict(s) resolved automatically.`}
        </div>
      </aside>
    </div>
  );
}
