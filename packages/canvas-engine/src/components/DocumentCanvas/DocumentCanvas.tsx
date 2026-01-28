/**
 * DocumentCanvas - Rich text document editor
 *
 * A basic contenteditable-based rich text editor for documents like
 * project charters, reports, and notes.
 */

import { useCallback, useRef, useEffect } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { CanvasArtifact } from '../../types/artifact';
import type { DocumentContent } from '../../types/artifact';
import styles from './DocumentCanvas.module.css';

export interface DocumentCanvasProps extends CanvasComponentProps<DocumentContent> {
  onSaveDraft?: (artifact: CanvasArtifact<DocumentContent>) => void;
  onPublish?: (artifact: CanvasArtifact<DocumentContent>) => void;
}

export function DocumentCanvas({
  artifact,
  readOnly = false,
  onChange,
  onSaveDraft,
  onPublish,
  className,
}: DocumentCanvasProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const isInitialMount = useRef(true);

  // Initialize editor content
  useEffect(() => {
    if (editorRef.current && isInitialMount.current) {
      editorRef.current.innerHTML = artifact.content.html || '';
      isInitialMount.current = false;
    }
  }, [artifact.content.html]);

  const handleInput = useCallback(() => {
    if (editorRef.current && onChange) {
      const html = editorRef.current.innerHTML;
      const plainText = editorRef.current.textContent || '';
      onChange({ html, plainText });
    }
  }, [onChange]);

  const execCommand = useCallback((command: string, value?: string) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
    handleInput();
  }, [handleInput]);

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      {!readOnly && (
        <div className={styles.formatBar}>
          <div className={styles.actionGroup}>
            <button
              className={styles.actionButton}
              onClick={() => onSaveDraft?.(artifact)}
              type="button"
            >
              Save Draft
            </button>
            <button
              className={`${styles.actionButton} ${styles.primaryAction}`}
              onClick={() => onPublish?.(artifact)}
              type="button"
            >
              Publish
            </button>
          </div>
          <div className={styles.separator} />
          <div className={styles.formatGroup}>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('bold')}
              title="Bold (Ctrl+B)"
              aria-label="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('italic')}
              title="Italic (Ctrl+I)"
              aria-label="Italic"
            >
              <em>I</em>
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('underline')}
              title="Underline (Ctrl+U)"
              aria-label="Underline"
            >
              <u>U</u>
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('strikeThrough')}
              title="Strikethrough"
              aria-label="Strikethrough"
            >
              <s>S</s>
            </button>
          </div>

          <div className={styles.separator} />

          <div className={styles.formatGroup}>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('formatBlock', 'h1')}
              title="Heading 1"
              aria-label="Heading 1"
            >
              H1
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('formatBlock', 'h2')}
              title="Heading 2"
              aria-label="Heading 2"
            >
              H2
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('formatBlock', 'h3')}
              title="Heading 3"
              aria-label="Heading 3"
            >
              H3
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('formatBlock', 'p')}
              title="Paragraph"
              aria-label="Paragraph"
            >
              P
            </button>
          </div>

          <div className={styles.separator} />

          <div className={styles.formatGroup}>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('insertUnorderedList')}
              title="Bullet list"
              aria-label="Bullet list"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="8" y1="6" x2="21" y2="6" />
                <line x1="8" y1="12" x2="21" y2="12" />
                <line x1="8" y1="18" x2="21" y2="18" />
                <circle cx="4" cy="6" r="1" fill="currentColor" />
                <circle cx="4" cy="12" r="1" fill="currentColor" />
                <circle cx="4" cy="18" r="1" fill="currentColor" />
              </svg>
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('insertOrderedList')}
              title="Numbered list"
              aria-label="Numbered list"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="10" y1="6" x2="21" y2="6" />
                <line x1="10" y1="12" x2="21" y2="12" />
                <line x1="10" y1="18" x2="21" y2="18" />
                <text x="3" y="8" fontSize="8" fill="currentColor">1</text>
                <text x="3" y="14" fontSize="8" fill="currentColor">2</text>
                <text x="3" y="20" fontSize="8" fill="currentColor">3</text>
              </svg>
            </button>
          </div>

          <div className={styles.separator} />

          <div className={styles.formatGroup}>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('undo')}
              title="Undo (Ctrl+Z)"
              aria-label="Undo"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 7v6h6" />
                <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
              </svg>
            </button>
            <button
              className={styles.formatButton}
              onClick={() => execCommand('redo')}
              title="Redo (Ctrl+Y)"
              aria-label="Redo"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 7v6h-6" />
                <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7" />
              </svg>
            </button>
          </div>
        </div>
      )}

      <div
        ref={editorRef}
        className={styles.editor}
        contentEditable={!readOnly}
        onInput={handleInput}
        onBlur={handleInput}
        role="textbox"
        aria-multiline="true"
        aria-label={`Edit ${artifact.title}`}
        data-placeholder="Start typing your document..."
      />
    </div>
  );
}
