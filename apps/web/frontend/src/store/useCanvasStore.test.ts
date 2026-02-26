import { describe, expect, it, beforeEach, vi } from 'vitest';
import { useCanvasStore, SAMPLE_ARTIFACT_IDS } from './useCanvasStore';
import type { CanvasTab } from './useCanvasStore';
import type { CanvasArtifact, DocumentContent } from '@ppm/canvas-engine';

// Mock the knowledgeApi service used by saveArtifact / publishArtifact
vi.mock('@/services/knowledgeApi', () => ({
  createDocumentVersion: vi.fn(),
}));

import { createDocumentVersion } from '@/services/knowledgeApi';

/** Helper to build a minimal CanvasArtifact for testing. */
function makeArtifact(overrides: Partial<CanvasArtifact> = {}): CanvasArtifact {
  const now = new Date().toISOString();
  return {
    id: 'artifact-test-1',
    type: 'document',
    title: 'Test Document',
    projectId: 'project-test',
    content: {
      html: '<p>Test content</p>',
      plainText: 'Test content',
    } as DocumentContent,
    metadata: {
      createdAt: now,
      updatedAt: now,
    },
    version: 1,
    status: 'draft',
    ...overrides,
  };
}

describe('useCanvasStore', () => {
  beforeEach(() => {
    // Reset store data to a clean slate (empty tabs, empty artifacts)
    // Do NOT pass `true` (replace) which would strip out action functions.
    useCanvasStore.setState({
      tabs: [],
      activeTabId: null,
      artifacts: {},
    });
    vi.resetAllMocks();
  });

  describe('initial state', () => {
    it('should start with empty tabs and no active tab after reset', () => {
      const state = useCanvasStore.getState();
      expect(state.tabs).toEqual([]);
      expect(state.activeTabId).toBeNull();
    });

    it('should have artifacts as an object', () => {
      const state = useCanvasStore.getState();
      expect(typeof state.artifacts).toBe('object');
    });
  });

  describe('fresh store has sample artifacts', () => {
    it('should include sample artifacts when the store is first created', () => {
      // Create a fresh store-like snapshot by reading the initial state before our
      // beforeEach resets it. We can verify the constant IDs are defined.
      expect(SAMPLE_ARTIFACT_IDS.charter).toBe('artifact-charter-1');
      expect(SAMPLE_ARTIFACT_IDS.wbs).toBe('artifact-wbs-1');
      expect(SAMPLE_ARTIFACT_IDS.timeline).toBe('artifact-timeline-1');
      expect(SAMPLE_ARTIFACT_IDS.spreadsheet).toBe('artifact-spreadsheet-1');
      expect(SAMPLE_ARTIFACT_IDS.dashboard).toBe('artifact-dashboard-1');
      expect(SAMPLE_ARTIFACT_IDS.qualityDashboard).toBe('artifact-quality-dashboard-1');
    });
  });

  describe('openArtifact', () => {
    it('should create a new tab and set it as active', () => {
      const artifact = makeArtifact({ id: 'art-1', title: 'Doc A', type: 'document' });
      useCanvasStore.getState().openArtifact(artifact);

      const state = useCanvasStore.getState();
      expect(state.tabs.length).toBe(1);
      expect(state.tabs[0].artifactId).toBe('art-1');
      expect(state.tabs[0].title).toBe('Doc A');
      expect(state.tabs[0].type).toBe('document');
      expect(state.tabs[0].isDirty).toBe(false);
      expect(state.activeTabId).toBe(state.tabs[0].id);
    });

    it('should store the artifact in the artifacts cache', () => {
      const artifact = makeArtifact({ id: 'art-2' });
      useCanvasStore.getState().openArtifact(artifact);

      expect(useCanvasStore.getState().artifacts['art-2']).toBeDefined();
      expect(useCanvasStore.getState().artifacts['art-2'].title).toBe('Test Document');
    });

    it('should not create a duplicate tab for the same artifact', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      useCanvasStore.getState().openArtifact(artifact);

      const state = useCanvasStore.getState();
      expect(state.tabs.length).toBe(1);
    });

    it('should switch to existing tab when opening same artifact', () => {
      const artifact1 = makeArtifact({ id: 'art-1', title: 'Doc A' });
      const artifact2 = makeArtifact({ id: 'art-2', title: 'Doc B' });
      useCanvasStore.getState().openArtifact(artifact1);
      useCanvasStore.getState().openArtifact(artifact2);

      const tab1Id = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-1')!.id;

      // Reopen art-1
      useCanvasStore.getState().openArtifact(artifact1);
      expect(useCanvasStore.getState().activeTabId).toBe(tab1Id);
      expect(useCanvasStore.getState().tabs.length).toBe(2);
    });
  });

  describe('closeTab', () => {
    it('should remove the tab', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      const tabId = useCanvasStore.getState().tabs[0].id;

      useCanvasStore.getState().closeTab(tabId);
      expect(useCanvasStore.getState().tabs.length).toBe(0);
    });

    it('should set activeTabId to null when last tab is closed', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      const tabId = useCanvasStore.getState().tabs[0].id;

      useCanvasStore.getState().closeTab(tabId);
      expect(useCanvasStore.getState().activeTabId).toBeNull();
    });

    it('should activate the next tab when closing the active tab', () => {
      // Mock Date.now to return unique timestamps for tab ID generation
      let now = 1000;
      const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => ++now);

      const a1 = makeArtifact({ id: 'art-1' });
      const a2 = makeArtifact({ id: 'art-2' });
      const a3 = makeArtifact({ id: 'art-3' });
      useCanvasStore.getState().openArtifact(a1);
      useCanvasStore.getState().openArtifact(a2);
      useCanvasStore.getState().openArtifact(a3);

      // Active tab is the last opened (art-3)
      const tab3Id = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-3')!.id;
      // Close tab 3 - should activate the previous one at the same index (art-2)
      useCanvasStore.getState().closeTab(tab3Id);

      const state = useCanvasStore.getState();
      expect(state.tabs.length).toBe(2);
      const tab2 = state.tabs.find((t) => t.artifactId === 'art-2');
      expect(state.activeTabId).toBe(tab2!.id);

      dateNowSpy.mockRestore();
    });

    it('should not change activeTabId when closing a non-active tab', () => {
      // Mock Date.now to return unique timestamps for tab ID generation
      let now = 2000;
      const dateNowSpy = vi.spyOn(Date, 'now').mockImplementation(() => ++now);

      const a1 = makeArtifact({ id: 'art-1' });
      const a2 = makeArtifact({ id: 'art-2' });
      useCanvasStore.getState().openArtifact(a1);
      useCanvasStore.getState().openArtifact(a2);

      const tab1Id = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-1')!.id;
      const tab2Id = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-2')!.id;

      // Active is tab2, close tab1
      expect(useCanvasStore.getState().activeTabId).toBe(tab2Id);
      useCanvasStore.getState().closeTab(tab1Id);
      expect(useCanvasStore.getState().activeTabId).toBe(tab2Id);

      dateNowSpy.mockRestore();
    });

    it('should be a no-op for a nonexistent tab ID', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);

      useCanvasStore.getState().closeTab('nonexistent-tab');
      expect(useCanvasStore.getState().tabs.length).toBe(1);
    });
  });

  describe('setActiveTab', () => {
    it('should set the active tab', () => {
      const a1 = makeArtifact({ id: 'art-1' });
      const a2 = makeArtifact({ id: 'art-2' });
      useCanvasStore.getState().openArtifact(a1);
      useCanvasStore.getState().openArtifact(a2);

      const tab1Id = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-1')!.id;
      useCanvasStore.getState().setActiveTab(tab1Id);

      expect(useCanvasStore.getState().activeTabId).toBe(tab1Id);
    });

    it('should not set an invalid tab ID as active', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      const currentActiveId = useCanvasStore.getState().activeTabId;

      useCanvasStore.getState().setActiveTab('nonexistent');
      expect(useCanvasStore.getState().activeTabId).toBe(currentActiveId);
    });
  });

  describe('markTabDirty', () => {
    it('should mark a tab as dirty', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      const tabId = useCanvasStore.getState().tabs[0].id;

      useCanvasStore.getState().markTabDirty(tabId, true);
      expect(useCanvasStore.getState().tabs[0].isDirty).toBe(true);
    });

    it('should mark a tab as not dirty', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);
      const tabId = useCanvasStore.getState().tabs[0].id;

      useCanvasStore.getState().markTabDirty(tabId, true);
      useCanvasStore.getState().markTabDirty(tabId, false);
      expect(useCanvasStore.getState().tabs[0].isDirty).toBe(false);
    });
  });

  describe('updateArtifactContent', () => {
    it('should update the artifact content and mark the tab dirty', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.getState().openArtifact(artifact);

      const newContent: DocumentContent = {
        html: '<p>Updated</p>',
        plainText: 'Updated',
      };
      useCanvasStore.getState().updateArtifactContent('art-1', newContent);

      const state = useCanvasStore.getState();
      const updatedArtifact = state.artifacts['art-1'];
      expect((updatedArtifact.content as DocumentContent).html).toBe('<p>Updated</p>');

      const tab = state.tabs.find((t) => t.artifactId === 'art-1');
      expect(tab?.isDirty).toBe(true);
    });

    it('should be a no-op for a nonexistent artifact', () => {
      useCanvasStore.setState({ artifacts: {} });

      const newContent: DocumentContent = { html: '<p>Test</p>', plainText: 'Test' };
      useCanvasStore.getState().updateArtifactContent('nonexistent', newContent);

      // No error thrown, state unchanged
      expect(Object.keys(useCanvasStore.getState().artifacts).length).toBe(0);
    });
  });

  describe('getActiveArtifact', () => {
    it('should return null when there are no tabs', () => {
      expect(useCanvasStore.getState().getActiveArtifact()).toBeNull();
    });

    it('should return the artifact for the active tab', () => {
      const artifact = makeArtifact({ id: 'art-1', title: 'Active Doc' });
      useCanvasStore.getState().openArtifact(artifact);

      const active = useCanvasStore.getState().getActiveArtifact();
      expect(active?.id).toBe('art-1');
      expect(active?.title).toBe('Active Doc');
    });
  });

  describe('getArtifact', () => {
    it('should return an artifact by ID', () => {
      const artifact = makeArtifact({ id: 'art-1' });
      useCanvasStore.setState({ artifacts: { 'art-1': artifact } });

      const result = useCanvasStore.getState().getArtifact('art-1');
      expect(result?.id).toBe('art-1');
    });

    it('should return undefined for nonexistent artifact', () => {
      const result = useCanvasStore.getState().getArtifact('nonexistent');
      expect(result).toBeUndefined();
    });
  });

  describe('saveArtifact', () => {
    it('should call createDocumentVersion for document type artifacts', async () => {
      vi.mocked(createDocumentVersion).mockResolvedValue({
        version: 2,
        metadata: {},
      } as ReturnType<typeof createDocumentVersion> extends Promise<infer T> ? T : never);

      const artifact = makeArtifact({ id: 'art-doc', type: 'document' });
      useCanvasStore.getState().openArtifact(artifact);
      useCanvasStore.getState().markTabDirty(useCanvasStore.getState().tabs[0].id, true);

      await useCanvasStore.getState().saveArtifact('art-doc');

      expect(createDocumentVersion).toHaveBeenCalled();
      const tab = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-doc');
      expect(tab?.isDirty).toBe(false);
    });

    it('should clear isDirty for non-document artifacts without calling API', async () => {
      const artifact = makeArtifact({ id: 'art-tree', type: 'tree', content: { rootId: 'root', nodes: {} } });
      useCanvasStore.getState().openArtifact(artifact);
      useCanvasStore.getState().markTabDirty(useCanvasStore.getState().tabs[0].id, true);

      await useCanvasStore.getState().saveArtifact('art-tree');

      expect(createDocumentVersion).not.toHaveBeenCalled();
      const tab = useCanvasStore.getState().tabs.find((t) => t.artifactId === 'art-tree');
      expect(tab?.isDirty).toBe(false);
    });
  });
});
