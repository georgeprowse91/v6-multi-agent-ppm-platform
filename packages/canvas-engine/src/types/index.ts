/**
 * Canvas Engine Types - Barrel export
 */

// Artifact types
export type {
  CanvasType,
  ArtifactStatus,
  DocumentContent,
  TreeNode,
  TreeContent,
  TimelineItem,
  TimelineContent,
  SpreadsheetCell,
  SpreadsheetContent,
  DashboardWidget,
  DashboardContent,
  BoardCard,
  BoardColumn,
  BoardContent,
  BacklogItem,
  BacklogContent,
  GanttTask,
  GanttContent,
  OptimizationSuggestion,
  ResourceUtilization,
  GridColumn,
  GridContent,
  FinancialLineItem,
  FinancialContent,
  DependencyNode,
  DependencyLink,
  DependencyMapContent,
  RoadmapMilestone,
  RoadmapContent,
  ApprovalHistoryEntry,
  ApprovalContent,
  ArtifactContent,
  ArtifactMetadata,
  CanvasArtifact,
  DocumentArtifact,
  TreeArtifact,
  TimelineArtifact,
  SpreadsheetArtifact,
  DashboardArtifact,
  BoardArtifact,
  BacklogArtifact,
  GanttArtifact,
  GridArtifact,
  FinancialArtifact,
  DependencyMapArtifact,
  RoadmapArtifact,
  ApprovalArtifact,
} from './artifact';

export { createArtifact, createEmptyContent } from './artifact';

// Canvas types
export type {
  CanvasComponentProps,
  CanvasTypeConfig,
  CanvasTab,
  TabAction,
  CanvasHostState,
} from './canvas';

export {
  CANVAS_TYPE_CONFIGS,
  initialCanvasHostState,
  canvasHostReducer,
} from './canvas';
