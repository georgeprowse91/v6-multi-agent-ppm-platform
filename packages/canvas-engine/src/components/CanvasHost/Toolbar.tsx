/**
 * Toolbar - Action toolbar for canvas operations
 */

import { useState } from 'react';
import type { CanvasArtifact } from '../../types/artifact';
import type { CanvasTypeConfig } from '../../types/canvas';
import styles from './Toolbar.module.css';

export interface ToolbarProps {
  artifact: CanvasArtifact;
  config: CanvasTypeConfig;
  onSaveDraft: () => void;
  onPublish: () => void;
  onExport: (format: string) => void;
}

export function Toolbar({
  artifact,
  config,
  onSaveDraft,
  onPublish,
  onExport,
}: ToolbarProps) {
  const [showExportMenu, setShowExportMenu] = useState(false);

  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <span className={styles.statusBadge} data-status={artifact.status}>
          {artifact.status === 'draft' ? 'Draft' : 'Published'}
        </span>
        <span className={styles.version}>v{artifact.version}</span>
      </div>

      <div className={styles.right}>
        <button
          className={`${styles.button} ${styles.secondary}`}
          onClick={onSaveDraft}
          title="Save as draft"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          Save Draft
        </button>

        <button
          className={`${styles.button} ${styles.primary}`}
          onClick={onPublish}
          title="Publish artifact"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Publish
        </button>

        {config.supportsExport && (
          <div className={styles.exportWrapper}>
            <button
              className={`${styles.button} ${styles.secondary}`}
              onClick={() => setShowExportMenu(!showExportMenu)}
              title="Export artifact"
              aria-expanded={showExportMenu}
              aria-haspopup="menu"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {showExportMenu && (
              <div className={styles.exportMenu} role="menu">
                {config.exportFormats?.map(format => (
                  <button
                    key={format}
                    className={styles.exportItem}
                    role="menuitem"
                    onClick={() => {
                      onExport(format);
                      setShowExportMenu(false);
                    }}
                  >
                    Export as .{format.toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
