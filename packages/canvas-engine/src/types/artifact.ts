/**
 * CanvasArtifact - The canonical interface for all canvas content types.
 *
 * This is the core data model that represents any content that can be
 * rendered and edited within the canvas framework.
 */

/** Supported canvas/artifact types */
export type CanvasType =
  | 'document'
  | 'tree'
  | 'timeline'
  | 'spreadsheet'
  | 'dashboard';

/** Publication status of an artifact */
export type ArtifactStatus = 'draft' | 'published';

/** Content types for different canvas types */
export interface DocumentContent {
  html: string;
  plainText?: string;
}

export interface ProvenanceMetadata {
  sourceAgent?: string;
  generatedAt?: string;
  correlationId?: string;
  inputContext?: Record<string, unknown>;
}

export interface EditHistoryEntry {
  version: number;
  status?: string;
  editedAt: string;
  editedBy?: string;
  source?: string;
  provenance?: ProvenanceMetadata;
}

export interface TreeNode {
  id: string;
  label: string;
  parentId: string | null;
  children: string[];
  metadata?: Record<string, unknown>;
  collapsed?: boolean;
}

export interface TreeContent {
  rootId: string;
  nodes: Record<string, TreeNode>;
}

export interface TimelineItem {
  id: string;
  name: string;
  startDate: string; // ISO date string
  endDate: string; // ISO date string
  progress?: number; // 0-100
  color?: string;
  dependencies?: string[];
  isMilestone?: boolean;
  gateStatus?: 'on-track' | 'delayed';
}

export interface TimelineContent {
  items: TimelineItem[];
  viewStart?: string;
  viewEnd?: string;
  wbs?: TreeContent;
}

export interface SpreadsheetCell {
  value: string | number | boolean | null;
  formula?: string;
  format?: string;
}

export interface SpreadsheetContent {
  columns: string[];
  rows: SpreadsheetCell[][];
  columnWidths?: Record<string, number>;
}

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric' | 'table' | 'text';
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  config: Record<string, unknown>;
}

export interface DashboardContent {
  widgets: DashboardWidget[];
  gridColumns?: number;
  gridRows?: number;
}

/** Union type for all content types */
export type ArtifactContent =
  | DocumentContent
  | TreeContent
  | TimelineContent
  | SpreadsheetContent
  | DashboardContent;

/** Metadata associated with an artifact */
export interface ArtifactMetadata {
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
  tags?: string[];
  description?: string;
  provenance?: ProvenanceMetadata;
  editHistory?: EditHistoryEntry[];
  [key: string]: unknown;
}

/**
 * CanvasArtifact - The core data model for canvas content.
 *
 * @example
 * const charter: CanvasArtifact<DocumentContent> = {
 *   id: 'artifact-123',
 *   type: 'document',
 *   title: 'Project Charter',
 *   projectId: 'project-456',
 *   content: { html: '<h1>Charter</h1><p>Content here...</p>' },
 *   metadata: { createdAt: '2024-01-15T10:00:00Z', updatedAt: '2024-01-15T10:00:00Z' },
 *   version: 1,
 *   status: 'draft'
 * };
 */
export interface CanvasArtifact<T extends ArtifactContent = ArtifactContent> {
  /** Unique identifier for the artifact */
  id: string;

  /** The type of canvas this artifact renders in */
  type: CanvasType;

  /** Display title for the artifact */
  title: string;

  /** The project this artifact belongs to */
  projectId: string;

  /** The actual content of the artifact (type-specific) */
  content: T;

  /** Additional metadata about the artifact */
  metadata: ArtifactMetadata;

  /** Version number for optimistic concurrency control */
  version: number;

  /** Publication status */
  status: ArtifactStatus;
}

/** Type-safe artifact types for each canvas type */
export type DocumentArtifact = CanvasArtifact<DocumentContent>;
export type TreeArtifact = CanvasArtifact<TreeContent>;
export type TimelineArtifact = CanvasArtifact<TimelineContent>;
export type SpreadsheetArtifact = CanvasArtifact<SpreadsheetContent>;
export type DashboardArtifact = CanvasArtifact<DashboardContent>;

/** Helper to create a new artifact with defaults */
export function createArtifact<T extends ArtifactContent>(
  type: CanvasType,
  title: string,
  projectId: string,
  content: T
): CanvasArtifact<T> {
  const now = new Date().toISOString();
  return {
    id: `artifact-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type,
    title,
    projectId,
    content,
    metadata: {
      createdAt: now,
      updatedAt: now,
    },
    version: 1,
    status: 'draft',
  };
}

/** Helper to create empty content for each canvas type */
export function createEmptyContent(type: CanvasType): ArtifactContent {
  switch (type) {
    case 'document':
      return { html: '', plainText: '' } as DocumentContent;
    case 'tree':
      return {
        rootId: 'root',
        nodes: {
          root: { id: 'root', label: 'Root', parentId: null, children: [] },
        },
      } as TreeContent;
    case 'timeline':
      return { items: [] } as TimelineContent;
    case 'spreadsheet':
      return {
        columns: ['A', 'B', 'C', 'D', 'E'],
        rows: Array(10).fill(null).map(() =>
          Array(5).fill(null).map(() => ({ value: null }))
        ),
      } as SpreadsheetContent;
    case 'dashboard':
      return { widgets: [], gridColumns: 12, gridRows: 8 } as DashboardContent;
  }
}
