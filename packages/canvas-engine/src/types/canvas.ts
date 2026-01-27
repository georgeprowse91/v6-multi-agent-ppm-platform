/**
 * Canvas component types and registry definitions.
 */

import type { CanvasArtifact, ArtifactContent, CanvasType } from './artifact';

/** Props that all canvas components receive */
export interface CanvasComponentProps<T extends ArtifactContent = ArtifactContent> {
  /** The artifact being rendered */
  artifact: CanvasArtifact<T>;

  /** Whether the canvas is in read-only mode */
  readOnly?: boolean;

  /** Callback when content changes */
  onChange?: (content: T) => void;

  /** Callback when the artifact should be saved */
  onSave?: () => void;

  /** Optional class name for styling */
  className?: string;
}

/** Configuration for a registered canvas type */
export interface CanvasTypeConfig {
  /** The canvas type identifier */
  type: CanvasType;

  /** Display name for the canvas type */
  displayName: string;

  /** Icon name (for use with icon library) */
  icon: string;

  /** Description of what this canvas type is for */
  description: string;

  /** Default title for new artifacts of this type */
  defaultTitle: string;

  /** Whether this canvas type supports export */
  supportsExport: boolean;

  /** Supported export formats */
  exportFormats?: string[];
}

/** The canvas type registry */
export const CANVAS_TYPE_CONFIGS: Record<CanvasType, CanvasTypeConfig> = {
  document: {
    type: 'document',
    displayName: 'Document',
    icon: 'file-text',
    description: 'Rich text documents like charters, reports, and notes',
    defaultTitle: 'Untitled Document',
    supportsExport: true,
    exportFormats: ['pdf', 'docx', 'html', 'md'],
  },
  tree: {
    type: 'tree',
    displayName: 'Structured Tree',
    icon: 'git-branch',
    description: 'Hierarchical structures like WBS, org charts, and taxonomies',
    defaultTitle: 'Untitled Tree',
    supportsExport: true,
    exportFormats: ['json', 'csv', 'png'],
  },
  timeline: {
    type: 'timeline',
    displayName: 'Timeline',
    icon: 'calendar',
    description: 'Gantt charts and project timelines',
    defaultTitle: 'Untitled Timeline',
    supportsExport: true,
    exportFormats: ['pdf', 'png', 'csv'],
  },
  spreadsheet: {
    type: 'spreadsheet',
    displayName: 'Spreadsheet',
    icon: 'table',
    description: 'Tabular data with calculations and formulas',
    defaultTitle: 'Untitled Spreadsheet',
    supportsExport: true,
    exportFormats: ['xlsx', 'csv', 'json'],
  },
  dashboard: {
    type: 'dashboard',
    displayName: 'Dashboard',
    icon: 'layout-dashboard',
    description: 'Visual dashboards with charts and metrics',
    defaultTitle: 'Untitled Dashboard',
    supportsExport: true,
    exportFormats: ['pdf', 'png'],
  },
};

/** Tab state for the canvas host */
export interface CanvasTab {
  /** Unique tab identifier */
  id: string;

  /** The artifact ID this tab displays */
  artifactId: string;

  /** The canvas type for this tab */
  type: CanvasType;

  /** Display title for the tab */
  title: string;

  /** Whether the tab has unsaved changes */
  isDirty: boolean;

  /** Timestamp when the tab was opened */
  openedAt: number;
}

/** Actions for tab management */
export type TabAction =
  | { type: 'OPEN_TAB'; payload: { artifact: CanvasArtifact } }
  | { type: 'CLOSE_TAB'; payload: { tabId: string } }
  | { type: 'SET_ACTIVE_TAB'; payload: { tabId: string } }
  | { type: 'MARK_DIRTY'; payload: { tabId: string; isDirty: boolean } }
  | { type: 'UPDATE_TITLE'; payload: { tabId: string; title: string } };

/** State for the canvas host */
export interface CanvasHostState {
  /** Currently open tabs */
  tabs: CanvasTab[];

  /** ID of the currently active tab */
  activeTabId: string | null;

  /** Cached artifacts (in-memory persistence) */
  artifacts: Record<string, CanvasArtifact>;
}

/** Initial state for canvas host */
export const initialCanvasHostState: CanvasHostState = {
  tabs: [],
  activeTabId: null,
  artifacts: {},
};

/** Reducer for canvas host state */
export function canvasHostReducer(
  state: CanvasHostState,
  action: TabAction
): CanvasHostState {
  switch (action.type) {
    case 'OPEN_TAB': {
      const { artifact } = action.payload;

      // Check if tab already exists
      const existingTab = state.tabs.find(t => t.artifactId === artifact.id);
      if (existingTab) {
        return { ...state, activeTabId: existingTab.id };
      }

      // Create new tab
      const newTab: CanvasTab = {
        id: `tab-${Date.now()}`,
        artifactId: artifact.id,
        type: artifact.type,
        title: artifact.title,
        isDirty: false,
        openedAt: Date.now(),
      };

      return {
        ...state,
        tabs: [...state.tabs, newTab],
        activeTabId: newTab.id,
        artifacts: {
          ...state.artifacts,
          [artifact.id]: artifact,
        },
      };
    }

    case 'CLOSE_TAB': {
      const { tabId } = action.payload;
      const tabIndex = state.tabs.findIndex(t => t.id === tabId);

      if (tabIndex === -1) return state;

      const newTabs = state.tabs.filter(t => t.id !== tabId);

      // Determine new active tab
      let newActiveTabId = state.activeTabId;
      if (state.activeTabId === tabId) {
        if (newTabs.length === 0) {
          newActiveTabId = null;
        } else if (tabIndex >= newTabs.length) {
          newActiveTabId = newTabs[newTabs.length - 1].id;
        } else {
          newActiveTabId = newTabs[tabIndex].id;
        }
      }

      return {
        ...state,
        tabs: newTabs,
        activeTabId: newActiveTabId,
      };
    }

    case 'SET_ACTIVE_TAB': {
      const { tabId } = action.payload;
      if (!state.tabs.some(t => t.id === tabId)) return state;
      return { ...state, activeTabId: tabId };
    }

    case 'MARK_DIRTY': {
      const { tabId, isDirty } = action.payload;
      return {
        ...state,
        tabs: state.tabs.map(t =>
          t.id === tabId ? { ...t, isDirty } : t
        ),
      };
    }

    case 'UPDATE_TITLE': {
      const { tabId, title } = action.payload;
      return {
        ...state,
        tabs: state.tabs.map(t =>
          t.id === tabId ? { ...t, title } : t
        ),
      };
    }

    default:
      return state;
  }
}
