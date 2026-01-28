/**
 * Canvas Store - Zustand store slice for canvas artifact management
 */

import { create } from 'zustand';
import type {
  CanvasArtifact,
  CanvasType,
  ArtifactContent,
  DocumentContent,
  TreeContent,
  TreeNode,
  TimelineContent,
  SpreadsheetContent,
  DashboardContent,
} from '@ppm/canvas-engine';
import { createDocumentVersion } from '@/services/knowledgeApi';
// createArtifact and createEmptyContent are used via @ppm/canvas-engine exports

export interface CanvasTab {
  id: string;
  artifactId: string;
  type: CanvasType;
  title: string;
  isDirty: boolean;
  openedAt: number;
}

interface CanvasStoreState {
  // Tabs
  tabs: CanvasTab[];
  activeTabId: string | null;

  // Artifacts (in-memory cache)
  artifacts: Record<string, CanvasArtifact>;

  // Tab actions
  openArtifact: (artifact: CanvasArtifact) => void;
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  markTabDirty: (tabId: string, isDirty: boolean) => void;

  // Artifact actions
  updateArtifactContent: (artifactId: string, content: ArtifactContent) => void;
  saveArtifact: (artifactId: string) => Promise<void>;
  publishArtifact: (artifactId: string) => Promise<void>;

  // Helper to get active artifact
  getActiveArtifact: () => CanvasArtifact | null;
  getArtifact: (artifactId: string) => CanvasArtifact | undefined;
}

// Sample artifacts for demonstration
function createSampleArtifacts(): Record<string, CanvasArtifact> {
  const now = new Date().toISOString();

  const charterDoc: CanvasArtifact<DocumentContent> = {
    id: 'artifact-charter-1',
    type: 'document',
    title: 'Project Charter',
    projectId: 'project-demo',
    content: {
      html: `<h1>Project Charter</h1>
<h2>Project Overview</h2>
<p>This document establishes the formal authorization for the project and provides the project manager with the authority to apply organizational resources to project activities.</p>
<h2>Project Purpose</h2>
<p>Define the business need or opportunity that the project addresses.</p>
<h2>Project Objectives</h2>
<ul>
<li>Objective 1: Deliver high-quality results</li>
<li>Objective 2: Meet timeline requirements</li>
<li>Objective 3: Stay within budget</li>
</ul>
<h2>Stakeholders</h2>
<p>Key stakeholders include the project sponsor, project team, and end users.</p>`,
      plainText: 'Project Charter\n\nProject Overview\nThis document establishes...',
    },
    metadata: { createdAt: now, updatedAt: now },
    version: 1,
    status: 'draft',
  };

  const rootNode: TreeNode = {
    id: 'wbs-root',
    label: 'Project Alpha - WBS',
    parentId: null,
    children: ['wbs-1', 'wbs-2', 'wbs-3'],
  };

  const wbsTree: CanvasArtifact<TreeContent> = {
    id: 'artifact-wbs-1',
    type: 'tree',
    title: 'Work Breakdown Structure',
    projectId: 'project-demo',
    content: {
      rootId: 'wbs-root',
      nodes: {
        'wbs-root': rootNode,
        'wbs-1': {
          id: 'wbs-1',
          label: '1. Initiation',
          parentId: 'wbs-root',
          children: ['wbs-1-1', 'wbs-1-2'],
        },
        'wbs-1-1': {
          id: 'wbs-1-1',
          label: '1.1 Project Charter',
          parentId: 'wbs-1',
          children: [],
        },
        'wbs-1-2': {
          id: 'wbs-1-2',
          label: '1.2 Stakeholder Analysis',
          parentId: 'wbs-1',
          children: [],
        },
        'wbs-2': {
          id: 'wbs-2',
          label: '2. Planning',
          parentId: 'wbs-root',
          children: ['wbs-2-1', 'wbs-2-2', 'wbs-2-3'],
        },
        'wbs-2-1': {
          id: 'wbs-2-1',
          label: '2.1 Scope Definition',
          parentId: 'wbs-2',
          children: [],
        },
        'wbs-2-2': {
          id: 'wbs-2-2',
          label: '2.2 Schedule Development',
          parentId: 'wbs-2',
          children: [],
        },
        'wbs-2-3': {
          id: 'wbs-2-3',
          label: '2.3 Resource Planning',
          parentId: 'wbs-2',
          children: [],
        },
        'wbs-3': {
          id: 'wbs-3',
          label: '3. Execution',
          parentId: 'wbs-root',
          children: ['wbs-3-1', 'wbs-3-2'],
        },
        'wbs-3-1': {
          id: 'wbs-3-1',
          label: '3.1 Development',
          parentId: 'wbs-3',
          children: [],
        },
        'wbs-3-2': {
          id: 'wbs-3-2',
          label: '3.2 Testing',
          parentId: 'wbs-3',
          children: [],
        },
      },
    },
    metadata: { createdAt: now, updatedAt: now },
    version: 1,
    status: 'draft',
  };

  const timeline: CanvasArtifact<TimelineContent> = {
    id: 'artifact-timeline-1',
    type: 'timeline',
    title: 'Project Schedule',
    projectId: 'project-demo',
    content: {
      items: [
        {
          id: 'task-1',
          name: 'Project Kickoff',
          startDate: '2024-02-01',
          endDate: '2024-02-07',
          progress: 100,
          color: '#22c55e',
        },
        {
          id: 'task-2',
          name: 'Requirements Gathering',
          startDate: '2024-02-05',
          endDate: '2024-02-20',
          progress: 75,
          color: '#6366f1',
        },
        {
          id: 'task-3',
          name: 'Design Phase',
          startDate: '2024-02-15',
          endDate: '2024-03-05',
          progress: 50,
          color: '#6366f1',
        },
        {
          id: 'task-4',
          name: 'Development Sprint 1',
          startDate: '2024-03-01',
          endDate: '2024-03-15',
          progress: 25,
          color: '#8b5cf6',
        },
        {
          id: 'task-5',
          name: 'Development Sprint 2',
          startDate: '2024-03-15',
          endDate: '2024-03-30',
          progress: 0,
          color: '#8b5cf6',
        },
      ],
    },
    metadata: { createdAt: now, updatedAt: now },
    version: 1,
    status: 'draft',
  };

  const spreadsheet: CanvasArtifact<SpreadsheetContent> = {
    id: 'artifact-spreadsheet-1',
    type: 'spreadsheet',
    title: 'Budget Tracker',
    projectId: 'project-demo',
    content: {
      columns: ['A', 'B', 'C', 'D'],
      rows: [
        [{ value: 'Category' }, { value: 'Planned' }, { value: 'Actual' }, { value: 'Variance' }],
        [{ value: 'Personnel' }, { value: 50000 }, { value: 48000 }, { value: 2000 }],
        [{ value: 'Equipment' }, { value: 15000 }, { value: 16500 }, { value: -1500 }],
        [{ value: 'Software' }, { value: 10000 }, { value: 9500 }, { value: 500 }],
        [{ value: 'Training' }, { value: 5000 }, { value: 4000 }, { value: 1000 }],
        [{ value: 'Total' }, { value: 80000 }, { value: 78000 }, { value: 2000 }],
      ],
    },
    metadata: { createdAt: now, updatedAt: now },
    version: 1,
    status: 'draft',
  };

  const dashboard: CanvasArtifact<DashboardContent> = {
    id: 'artifact-dashboard-1',
    type: 'dashboard',
    title: 'Project Dashboard',
    projectId: 'project-demo',
    content: {
      widgets: [
        {
          id: 'widget-1',
          type: 'metric',
          title: 'Budget Health',
          x: 0,
          y: 0,
          width: 3,
          height: 2,
          config: { value: 97, unit: '%', change: 2 },
        },
        {
          id: 'widget-2',
          type: 'metric',
          title: 'Tasks Completed',
          x: 3,
          y: 0,
          width: 3,
          height: 2,
          config: { value: 42, unit: '/50', change: 8 },
        },
        {
          id: 'widget-3',
          type: 'metric',
          title: 'Schedule Variance',
          x: 6,
          y: 0,
          width: 3,
          height: 2,
          config: { value: -3, unit: 'days', change: -5 },
        },
        {
          id: 'widget-4',
          type: 'metric',
          title: 'Team Velocity',
          x: 9,
          y: 0,
          width: 3,
          height: 2,
          config: { value: 24, unit: 'pts', change: 12 },
        },
        {
          id: 'widget-5',
          type: 'chart',
          title: 'Progress Over Time',
          x: 0,
          y: 2,
          width: 6,
          height: 3,
          config: { chartType: 'line' },
        },
        {
          id: 'widget-6',
          type: 'chart',
          title: 'Budget by Category',
          x: 6,
          y: 2,
          width: 6,
          height: 3,
          config: { chartType: 'pie' },
        },
      ],
      gridColumns: 12,
      gridRows: 8,
    },
    metadata: { createdAt: now, updatedAt: now },
    version: 1,
    status: 'draft',
  };

  return {
    [charterDoc.id]: charterDoc,
    [wbsTree.id]: wbsTree,
    [timeline.id]: timeline,
    [spreadsheet.id]: spreadsheet,
    [dashboard.id]: dashboard,
  };
}

export const useCanvasStore = create<CanvasStoreState>((set, get) => ({
  tabs: [],
  activeTabId: null,
  artifacts: createSampleArtifacts(),

  openArtifact: (artifact) => {
    set((state) => {
      // Check if tab already exists for this artifact
      const existingTab = state.tabs.find((t) => t.artifactId === artifact.id);
      if (existingTab) {
        return { activeTabId: existingTab.id };
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
        tabs: [...state.tabs, newTab],
        activeTabId: newTab.id,
        artifacts: {
          ...state.artifacts,
          [artifact.id]: artifact,
        },
      };
    });
  },

  closeTab: (tabId) => {
    set((state) => {
      const tabIndex = state.tabs.findIndex((t) => t.id === tabId);
      if (tabIndex === -1) return state;

      const newTabs = state.tabs.filter((t) => t.id !== tabId);

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
        tabs: newTabs,
        activeTabId: newActiveTabId,
      };
    });
  },

  setActiveTab: (tabId) => {
    set((state) => {
      if (!state.tabs.some((t) => t.id === tabId)) return state;
      return { activeTabId: tabId };
    });
  },

  markTabDirty: (tabId, isDirty) => {
    set((state) => ({
      tabs: state.tabs.map((t) =>
        t.id === tabId ? { ...t, isDirty } : t
      ),
    }));
  },

  updateArtifactContent: (artifactId, content) => {
    set((state) => {
      const artifact = state.artifacts[artifactId];
      if (!artifact) return state;

      const updatedArtifact = {
        ...artifact,
        content,
        metadata: {
          ...artifact.metadata,
          updatedAt: new Date().toISOString(),
        },
      };

      // Mark tab as dirty
      const tab = state.tabs.find((t) => t.artifactId === artifactId);

      return {
        artifacts: {
          ...state.artifacts,
          [artifactId]: updatedArtifact,
        },
        tabs: tab
          ? state.tabs.map((t) =>
              t.id === tab.id ? { ...t, isDirty: true } : t
            )
          : state.tabs,
      };
    });
  },

  saveArtifact: async (artifactId) => {
    const artifact = get().artifacts[artifactId];
    if (!artifact) return;

    if (artifact.type === 'document') {
      try {
        const response = await createDocumentVersion({
          projectId: artifact.projectId,
          documentKey: artifact.id,
          name: artifact.title,
          docType: artifact.type,
          classification: 'internal',
          status: 'draft',
          content: artifact.content.html ?? artifact.content.plainText ?? '',
          metadata: {
            ...artifact.metadata,
            savedAt: new Date().toISOString(),
          },
        });
        set((state) => ({
          artifacts: {
            ...state.artifacts,
            [artifactId]: {
              ...artifact,
              status: 'draft',
              version: response.version,
              metadata: {
                ...artifact.metadata,
                updatedAt: new Date().toISOString(),
                repositoryVersion: response.version,
              },
            },
          },
          tabs: state.tabs.map((t) =>
            t.artifactId === artifactId ? { ...t, isDirty: false } : t
          ),
        }));
        return;
      } catch (error) {
        console.error('Failed to save artifact', error);
        return;
      }
    }

    set((state) => ({
      tabs: state.tabs.map((t) =>
        t.artifactId === artifactId ? { ...t, isDirty: false } : t
      ),
    }));
  },

  publishArtifact: async (artifactId) => {
    const artifact = get().artifacts[artifactId];
    if (!artifact) return;

    if (artifact.type === 'document') {
      try {
        const response = await createDocumentVersion({
          projectId: artifact.projectId,
          documentKey: artifact.id,
          name: artifact.title,
          docType: artifact.type,
          classification: 'internal',
          status: 'published',
          content: artifact.content.html ?? artifact.content.plainText ?? '',
          metadata: {
            ...artifact.metadata,
            publishedAt: new Date().toISOString(),
          },
        });
        set((state) => ({
          artifacts: {
            ...state.artifacts,
            [artifactId]: {
              ...artifact,
              status: 'published',
              version: response.version,
              metadata: {
                ...artifact.metadata,
                updatedAt: new Date().toISOString(),
                repositoryVersion: response.version,
              },
            },
          },
          tabs: state.tabs.map((t) =>
            t.artifactId === artifactId ? { ...t, isDirty: false } : t
          ),
        }));
        return;
      } catch (error) {
        console.error('Failed to publish artifact', error);
        return;
      }
    }

    set((state) => ({
      tabs: state.tabs.map((t) =>
        t.artifactId === artifactId ? { ...t, isDirty: false } : t
      ),
    }));
  },

  getActiveArtifact: () => {
    const state = get();
    const activeTab = state.tabs.find((t) => t.id === state.activeTabId);
    if (!activeTab) return null;
    return state.artifacts[activeTab.artifactId] ?? null;
  },

  getArtifact: (artifactId) => {
    return get().artifacts[artifactId];
  },
}));

// Export sample artifact IDs for use in the UI
export const SAMPLE_ARTIFACT_IDS = {
  charter: 'artifact-charter-1',
  wbs: 'artifact-wbs-1',
  timeline: 'artifact-timeline-1',
  spreadsheet: 'artifact-spreadsheet-1',
  dashboard: 'artifact-dashboard-1',
};
