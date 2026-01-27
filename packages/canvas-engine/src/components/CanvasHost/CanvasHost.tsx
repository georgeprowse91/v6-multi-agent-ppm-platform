/**
 * CanvasHost - Main container component for managing canvas tabs
 *
 * Provides:
 * - Tab bar with open/close/switch functionality
 * - Standard toolbar area (Save Draft / Publish / Export)
 * - Per-tab persisted state (in-memory)
 */

import { useCallback, type ReactNode } from 'react';
import type { CanvasArtifact, CanvasType, ArtifactContent } from '../../types/artifact';
import type { CanvasTab } from '../../types/canvas';
import { CANVAS_TYPE_CONFIGS } from '../../types/canvas';
import { TabBar } from './TabBar';
import { Toolbar } from './Toolbar';
import styles from './CanvasHost.module.css';

export interface CanvasHostProps {
  /** Currently open tabs */
  tabs: CanvasTab[];

  /** ID of the active tab */
  activeTabId: string | null;

  /** Get artifact by ID */
  getArtifact: (artifactId: string) => CanvasArtifact | undefined;

  /** Callback when a tab is selected */
  onTabSelect: (tabId: string) => void;

  /** Callback when a tab is closed */
  onTabClose: (tabId: string) => void;

  /** Callback when content changes */
  onContentChange?: (artifactId: string, content: ArtifactContent) => void;

  /** Callback when Save Draft is clicked */
  onSaveDraft?: (artifact: CanvasArtifact) => void;

  /** Callback when Publish is clicked */
  onPublish?: (artifact: CanvasArtifact) => void;

  /** Callback when Export is clicked */
  onExport?: (artifact: CanvasArtifact, format: string) => void;

  /** Render function for canvas content */
  renderCanvas: (
    type: CanvasType,
    artifact: CanvasArtifact,
    onChange: (content: ArtifactContent) => void
  ) => ReactNode;

  /** Optional empty state when no tabs are open */
  emptyState?: ReactNode;

  /** Optional class name */
  className?: string;
}

export function CanvasHost({
  tabs,
  activeTabId,
  getArtifact,
  onTabSelect,
  onTabClose,
  onContentChange,
  onSaveDraft,
  onPublish,
  onExport,
  renderCanvas,
  emptyState,
  className,
}: CanvasHostProps) {
  const activeTab = tabs.find(t => t.id === activeTabId);
  const activeArtifact = activeTab ? getArtifact(activeTab.artifactId) : undefined;

  const handleContentChange = useCallback(
    (content: ArtifactContent) => {
      if (activeArtifact && onContentChange) {
        onContentChange(activeArtifact.id, content);
      }
    },
    [activeArtifact, onContentChange]
  );

  const handleSaveDraft = useCallback(() => {
    if (activeArtifact && onSaveDraft) {
      onSaveDraft(activeArtifact);
    }
  }, [activeArtifact, onSaveDraft]);

  const handlePublish = useCallback(() => {
    if (activeArtifact && onPublish) {
      onPublish(activeArtifact);
    }
  }, [activeArtifact, onPublish]);

  const handleExport = useCallback(
    (format: string) => {
      if (activeArtifact && onExport) {
        onExport(activeArtifact, format);
      }
    },
    [activeArtifact, onExport]
  );

  const canvasConfig = activeArtifact
    ? CANVAS_TYPE_CONFIGS[activeArtifact.type]
    : null;

  return (
    <div className={`${styles.host} ${className ?? ''}`}>
      {tabs.length > 0 && (
        <TabBar
          tabs={tabs}
          activeTabId={activeTabId}
          onTabSelect={onTabSelect}
          onTabClose={onTabClose}
        />
      )}

      {activeArtifact && canvasConfig && (
        <Toolbar
          artifact={activeArtifact}
          config={canvasConfig}
          onSaveDraft={handleSaveDraft}
          onPublish={handlePublish}
          onExport={handleExport}
        />
      )}

      <div className={styles.canvasArea}>
        {activeArtifact ? (
          renderCanvas(activeArtifact.type, activeArtifact, handleContentChange)
        ) : (
          emptyState ?? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M9 3v18" />
                  <path d="M3 9h6" />
                </svg>
              </div>
              <h3 className={styles.emptyTitle}>No canvas open</h3>
              <p className={styles.emptyText}>
                Open a document, tree, timeline, or other artifact to get started.
              </p>
            </div>
          )
        )}
      </div>
    </div>
  );
}
