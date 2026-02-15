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
  BoardCanvas,
  BacklogCanvas,
  GanttCanvas,
  GridCanvas,
  FinancialCanvas,
  DependencyMapCanvas,
  RoadmapCanvas,
  ApprovalCanvas,
  type CanvasArtifact,
  type CanvasType,
  type ArtifactContent,
  type DocumentContent,
  type TreeContent,
  type TimelineContent,
  type SpreadsheetContent,
  type DashboardContent,
  type BoardContent,
  type BacklogContent,
  type GanttContent,
  type GridContent,
  type FinancialContent,
  type DependencyMapContent,
  type RoadmapContent,
  type ApprovalContent,
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
  const unifiedDashboardsEnabled = featureFlags.unified_dashboards === true;

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
      const payload = format === 'json'
        ? JSON.stringify(artifact.content, null, 2)
        : format === 'csv'
          ? 'id,title\n' + (Array.isArray((artifact.content as unknown as { items?: unknown }).items)
              ? ((artifact.content as { items: Array<{ id?: string; title?: string }> }).items
                  .map((item) => `${item.id ?? ''},${item.title ?? ''}`)
                  .join('\n'))
              : '')
          : `Export(${format}) for ${artifact.title}`;
      console.log(`Exporting ${artifact.title} as ${format}`, payload);
      alert(`Prepared ${format.toUpperCase()} export for ${artifact.title}.`);
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
              unifiedDashboardsEnabled={unifiedDashboardsEnabled}
            />
          );

        case 'board':
          return <BoardCanvas artifact={artifact as CanvasArtifact<BoardContent>} onChange={onChange as (content: BoardContent) => void} />;
        case 'backlog':
          return <BacklogCanvas artifact={artifact as CanvasArtifact<BacklogContent>} onChange={onChange as (content: BacklogContent) => void} />;
        case 'gantt':
          return <GanttCanvas artifact={artifact as CanvasArtifact<GanttContent>} onChange={onChange as (content: GanttContent) => void} />;
        case 'grid':
          return <GridCanvas artifact={artifact as CanvasArtifact<GridContent>} onChange={onChange as (content: GridContent) => void} />;
        case 'financial':
          return <FinancialCanvas artifact={artifact as CanvasArtifact<FinancialContent>} onChange={onChange as (content: FinancialContent) => void} />;
        case 'dependency_map':
          return <DependencyMapCanvas artifact={artifact as CanvasArtifact<DependencyMapContent>} onChange={onChange as (content: DependencyMapContent) => void} />;
        case 'roadmap':
          return <RoadmapCanvas artifact={artifact as CanvasArtifact<RoadmapContent>} onChange={onChange as (content: RoadmapContent) => void} />;
        case 'approval':
          return <ApprovalCanvas artifact={artifact as CanvasArtifact<ApprovalContent>} onChange={onChange as (content: ApprovalContent) => void} />;
        default:
          return <div>Unknown canvas type: {type}</div>;
      }
    },
    [autonomousDeliverablesEnabled, handlePublish, handleSaveDraft, unifiedDashboardsEnabled]
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
                      board: 'artifact.tree',
                      backlog: 'artifact.spreadsheet',
                      gantt: 'artifact.timeline',
                      grid: 'artifact.spreadsheet',
                      financial: 'artifact.dashboard',
                      dependency_map: 'artifact.tree',
                      roadmap: 'artifact.timeline',
                      approval: 'artifact.document',
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
