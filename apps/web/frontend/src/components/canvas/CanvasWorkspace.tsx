/**
 * CanvasWorkspace - Integrates the canvas-engine with the web app
 *
 * This component bridges the canvas-engine package with the application,
 * providing state management and rendering of canvas content.
 */

import { useCallback } from 'react';
import {
  CanvasHost,
  DocumentCanvas,
  StructuredTreeCanvas,
  TimelineCanvas,
  SpreadsheetCanvas,
  DashboardCanvas,
  type CanvasArtifact,
  type CanvasType,
  type ArtifactContent,
  type DocumentContent,
  type TreeContent,
  type TimelineContent,
  type SpreadsheetContent,
  type DashboardContent,
} from '@ppm/canvas-engine';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useAppStore } from '@/store/useAppStore';
import { Icon } from '@/components/icon/Icon';
import type { IconSemantic } from '@/components/icon/iconMap';
import styles from './CanvasWorkspace.module.css';

export function CanvasWorkspace() {
  const {
    tabs,
    activeTabId,
    setActiveTab,
    closeTab,
    updateArtifactContent,
    saveArtifact,
    publishArtifact,
    getArtifact,
  } = useCanvasStore();
  const { featureFlags } = useAppStore();
  const autonomousDeliverablesEnabled = featureFlags.autonomous_deliverables === true;

  const handleContentChange = useCallback(
    (artifactId: string, content: ArtifactContent) => {
      updateArtifactContent(artifactId, content);
    },
    [updateArtifactContent]
  );

  const handleSaveDraft = useCallback(
    (artifact: CanvasArtifact) => {
      saveArtifact(artifact.id);
    },
    [saveArtifact]
  );

  const handlePublish = useCallback(
    (artifact: CanvasArtifact) => {
      publishArtifact(artifact.id);
    },
    [publishArtifact]
  );

  const handleExport = useCallback(
    (artifact: CanvasArtifact, format: string) => {
      // In a real app, this would trigger an export
      console.log(`Exporting ${artifact.title} as ${format}`);
      alert(`Export to ${format.toUpperCase()} would be triggered here.\n\nArtifact: ${artifact.title}`);
    },
    []
  );

  const renderCanvas = useCallback(
    (
      type: CanvasType,
      artifact: CanvasArtifact,
      onChange: (content: ArtifactContent) => void
    ) => {
      switch (type) {
        case 'document':
          return (
            <DocumentCanvas
              artifact={artifact as CanvasArtifact<DocumentContent>}
              onChange={onChange as (content: DocumentContent) => void}
              onSaveDraft={handleSaveDraft}
              onPublish={handlePublish}
              showProvenance={autonomousDeliverablesEnabled}
            />
          );
        case 'tree':
          return (
            <StructuredTreeCanvas
              artifact={artifact as CanvasArtifact<TreeContent>}
              onChange={onChange as (content: TreeContent) => void}
            />
          );
        case 'timeline':
          return (
            <TimelineCanvas
              artifact={artifact as CanvasArtifact<TimelineContent>}
              onChange={onChange as (content: TimelineContent) => void}
            />
          );
        case 'spreadsheet':
          return (
            <SpreadsheetCanvas
              artifact={artifact as CanvasArtifact<SpreadsheetContent>}
              onChange={onChange as (content: SpreadsheetContent) => void}
            />
          );
        case 'dashboard':
          return (
            <DashboardCanvas
              artifact={artifact as CanvasArtifact<DashboardContent>}
              onChange={onChange as (content: DashboardContent) => void}
            />
          );
        default:
          return <div>Unknown canvas type: {type}</div>;
      }
    },
    []
  );

  // Convert store tabs to canvas-engine tab format
  const canvasTabs = tabs.map((tab) => ({
    id: tab.id,
    artifactId: tab.artifactId,
    type: tab.type,
    title: tab.title,
    isDirty: tab.isDirty,
    openedAt: tab.openedAt,
  }));

  return (
    <div className={styles.workspace}>
      <CanvasHost
        tabs={canvasTabs}
        activeTabId={activeTabId}
        getArtifact={getArtifact}
        onTabSelect={setActiveTab}
        onTabClose={closeTab}
        onContentChange={handleContentChange}
        onSaveDraft={handleSaveDraft}
        onPublish={handlePublish}
        onExport={handleExport}
        renderCanvas={renderCanvas}
        emptyState={<CanvasEmptyState />}
      />
    </div>
  );
}

/** Empty state component when no tabs are open */
function CanvasEmptyState() {
  const { artifacts, openArtifact } = useCanvasStore();

  // Show demo artifacts
  const demoArtifacts = Object.values(artifacts).slice(0, 5);

  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>
        <Icon semantic="artifact.document" decorative size="3xl" />
      </div>
      <h3 className={styles.emptyTitle}>No canvas open</h3>
      <p className={styles.emptyText}>
        Open an artifact from the list below or use the navigation panel.
      </p>

      <div className={styles.quickOpen}>
        <h4 className={styles.quickOpenTitle}>Quick Open</h4>
        <div className={styles.artifactList}>
          {demoArtifacts.map((artifact) => (
            <button
              key={artifact.id}
              className={styles.artifactButton}
              onClick={() => openArtifact(artifact)}
            >
              <span className={styles.artifactIcon}>
                <Icon
                  semantic={
                    ({
                      document: 'artifact.document',
                      tree: 'artifact.tree',
                      timeline: 'artifact.timeline',
                      spreadsheet: 'artifact.spreadsheet',
                      dashboard: 'artifact.dashboard',
                    } as Record<string, IconSemantic>)[artifact.type]
                  }
                  decorative
                  size="lg"
                />
              </span>
              <span className={styles.artifactInfo}>
                <span className={styles.artifactName}>{artifact.title}</span>
                <span className={styles.artifactType}>{artifact.type}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
