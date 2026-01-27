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
  ArtifactContent,
  ArtifactMetadata,
  CanvasArtifact,
  DocumentArtifact,
  TreeArtifact,
  TimelineArtifact,
  SpreadsheetArtifact,
  DashboardArtifact,
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
