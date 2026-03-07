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
  | 'dashboard'
  | 'board'
  | 'backlog'
  | 'gantt'
  | 'grid'
  | 'financial'
  | 'dependency_map'
  | 'roadmap'
  | 'approval';

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

export interface BoardCard {
  id: string;
  title: string;
  description?: string;
}

export interface BoardColumn {
  id: string;
  title: string;
  cards: BoardCard[];
}

export interface BoardContent { columns: BoardColumn[] }

export interface BacklogItem {
  id: string;
  title: string;
  parentId: string | null;
  rank: number;
  estimate: number;
}

export interface BacklogContent { items: BacklogItem[] }

export interface GanttTask {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  baselineStart?: string;
  baselineEnd?: string;
  dependencies: string[];
  progress?: number;
  color?: string;
  isMilestone?: boolean;
  resourceId?: string;
  isCritical?: boolean;
  slack?: number;
}

export interface OptimizationSuggestion {
  id: string;
  type: 'parallel_tasks' | 'fast_track' | 'crash' | 'resource_level';
  description: string;
  affectedTaskIds: string[];
  projectedSavingDays: number;
  status: 'pending' | 'accepted' | 'rejected';
}

export interface ResourceUtilization {
  resourceId: string;
  resourceName: string;
  dailyUtilization: { date: string; percent: number }[];
}

export interface GanttContent {
  tasks: GanttTask[];
  viewStart?: string;
  viewEnd?: string;
  optimizationSuggestions?: OptimizationSuggestion[];
  resourceUtilization?: ResourceUtilization[];
  showBaseline?: boolean;
  showCriticalPath?: boolean;
  showResourceChart?: boolean;
}

export interface GridColumn {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select';
  required?: boolean;
  options?: string[];
}

export interface GridContent {
  columns: GridColumn[];
  rows: Record<string, string | number>[];
}

export interface FinancialLineItem {
  id: string;
  category: string;
  budget: number;
  actual: number;
  forecast: number;
}

export interface FinancialContent {
  version: string;
  lineItems: FinancialLineItem[];
}

export interface DependencyNode { id: string; label: string }
export interface DependencyLink { source: string; target: string }
export interface DependencyMapContent {
  nodes: DependencyNode[];
  links: DependencyLink[];
}

export interface RoadmapMilestone {
  id: string;
  title: string;
  lane: string;
  startDate: string;
  endDate: string;
}

export interface RoadmapContent {
  lanes: string[];
  milestones: RoadmapMilestone[];
}

export interface ApprovalHistoryEntry {
  id: string;
  action: 'submit' | 'approve' | 'reject' | 'request_changes';
  actor: string;
  timestamp: string;
  note?: string;
}

export interface ApprovalContent {
  status: 'pending' | 'approved' | 'rejected';
  evidence: string[];
  history: ApprovalHistoryEntry[];
}

/** Union type for all content types */
export type ArtifactContent =
  | DocumentContent
  | TreeContent
  | TimelineContent
  | SpreadsheetContent
  | DashboardContent
  | BoardContent
  | BacklogContent
  | GanttContent
  | GridContent
  | FinancialContent
  | DependencyMapContent
  | RoadmapContent
  | ApprovalContent;

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
export type BoardArtifact = CanvasArtifact<BoardContent>;
export type BacklogArtifact = CanvasArtifact<BacklogContent>;
export type GanttArtifact = CanvasArtifact<GanttContent>;
export type GridArtifact = CanvasArtifact<GridContent>;
export type FinancialArtifact = CanvasArtifact<FinancialContent>;
export type DependencyMapArtifact = CanvasArtifact<DependencyMapContent>;
export type RoadmapArtifact = CanvasArtifact<RoadmapContent>;
export type ApprovalArtifact = CanvasArtifact<ApprovalContent>;

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
    case 'board':
      return {
        columns: [
          { id: 'col-todo', title: 'To Do', cards: [] },
          { id: 'col-progress', title: 'In Progress', cards: [] },
          { id: 'col-done', title: 'Done', cards: [] },
        ],
      } as BoardContent;
    case 'backlog':
      return { items: [] } as BacklogContent;
    case 'gantt':
      return { tasks: [], showBaseline: false, showCriticalPath: true, showResourceChart: false } as GanttContent;
    case 'grid':
      return {
        columns: [
          { key: 'name', label: 'Name', type: 'text', required: true },
          { key: 'status', label: 'Status', type: 'select', options: ['Open', 'Closed'] },
        ],
        rows: [],
      } as GridContent;
    case 'financial':
      return { version: 'v1', lineItems: [] } as FinancialContent;
    case 'dependency_map':
      return { nodes: [], links: [] } as DependencyMapContent;
    case 'roadmap':
      return { lanes: ['Now', 'Next', 'Later'], milestones: [] } as RoadmapContent;
    case 'approval':
      return { status: 'pending', evidence: [], history: [] } as ApprovalContent;
  }
}
