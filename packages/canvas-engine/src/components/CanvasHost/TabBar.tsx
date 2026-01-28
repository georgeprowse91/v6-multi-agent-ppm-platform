/**
 * TabBar - Tab navigation component for CanvasHost
 */

import type { CanvasTab } from '../../types/canvas';
import { CANVAS_TYPE_CONFIGS } from '../../types/canvas';
import styles from './TabBar.module.css';

export interface TabBarProps {
  tabs: CanvasTab[];
  activeTabId: string | null;
  onTabSelect: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
}

/** Simple icon component for canvas types */
function CanvasIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    document: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
    tree: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="6" y1="3" x2="6" y2="15" />
        <circle cx="18" cy="6" r="3" />
        <circle cx="6" cy="18" r="3" />
        <path d="M18 9a9 9 0 0 1-9 9" />
      </svg>
    ),
    timeline: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
    spreadsheet: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="3" y1="15" x2="21" y2="15" />
        <line x1="9" y1="3" x2="9" y2="21" />
        <line x1="15" y1="3" x2="15" y2="21" />
      </svg>
    ),
    dashboard: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="9" />
        <rect x="14" y="3" width="7" height="5" />
        <rect x="14" y="12" width="7" height="9" />
        <rect x="3" y="16" width="7" height="5" />
      </svg>
    ),
  };

  return <span className={styles.tabIcon}>{icons[type] ?? icons.document}</span>;
}

export function TabBar({ tabs, activeTabId, onTabSelect, onTabClose }: TabBarProps) {
  return (
    <div className={styles.tabBar} role="tablist">
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTabId;
        const config = CANVAS_TYPE_CONFIGS[tab.type];
        const focusTabByIndex = (nextIndex: number) => {
          const target = tabs[nextIndex];
          if (target) {
            onTabSelect(target.id);
          }
        };

        return (
          <div
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            className={`${styles.tab} ${isActive ? styles.active : ''}`}
            onClick={() => onTabSelect(tab.id)}
            onKeyDown={e => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onTabSelect(tab.id);
                return;
              }
              if (e.key === 'ArrowRight') {
                e.preventDefault();
                focusTabByIndex((index + 1) % tabs.length);
                return;
              }
              if (e.key === 'ArrowLeft') {
                e.preventDefault();
                focusTabByIndex((index - 1 + tabs.length) % tabs.length);
                return;
              }
              if (e.key === 'Home') {
                e.preventDefault();
                focusTabByIndex(0);
                return;
              }
              if (e.key === 'End') {
                e.preventDefault();
                focusTabByIndex(tabs.length - 1);
              }
            }}
            tabIndex={isActive ? 0 : -1}
            id={`canvas-tab-${tab.id}`}
          >
            <CanvasIcon type={tab.type} />
            <span className={styles.tabTitle} title={tab.title}>
              {tab.title}
            </span>
            {tab.isDirty && <span className={styles.dirtyIndicator} title="Unsaved changes" />}
            <button
              className={styles.closeButton}
              onClick={e => {
                e.stopPropagation();
                onTabClose(tab.id);
              }}
              title={`Close ${config.displayName}`}
              aria-label={`Close ${tab.title}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        );
      })}
    </div>
  );
}
