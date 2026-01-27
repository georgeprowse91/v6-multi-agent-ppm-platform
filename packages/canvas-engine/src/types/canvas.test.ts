/**
 * Tests for Canvas state management and reducers
 */

import { describe, it, expect } from 'vitest';
import {
  canvasHostReducer,
  initialCanvasHostState,
  CANVAS_TYPE_CONFIGS,
  type CanvasHostState,
  type TabAction,
} from './canvas';
import type { CanvasArtifact, DocumentContent } from './artifact';

// Helper to create a test artifact
function createTestArtifact(id: string, title: string = 'Test'): CanvasArtifact<DocumentContent> {
  return {
    id,
    type: 'document',
    title,
    projectId: 'test-project',
    content: { html: '', plainText: '' },
    metadata: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    version: 1,
    status: 'draft',
  };
}

describe('canvasHostReducer', () => {
  describe('OPEN_TAB', () => {
    it('should open a new tab for an artifact', () => {
      const artifact = createTestArtifact('art-1', 'My Document');
      const action: TabAction = { type: 'OPEN_TAB', payload: { artifact } };

      const newState = canvasHostReducer(initialCanvasHostState, action);

      expect(newState.tabs).toHaveLength(1);
      expect(newState.tabs[0].artifactId).toBe('art-1');
      expect(newState.tabs[0].title).toBe('My Document');
      expect(newState.tabs[0].type).toBe('document');
      expect(newState.tabs[0].isDirty).toBe(false);
      expect(newState.activeTabId).toBe(newState.tabs[0].id);
      expect(newState.artifacts['art-1']).toEqual(artifact);
    });

    it('should activate existing tab instead of creating duplicate', () => {
      const artifact = createTestArtifact('art-1');
      const state: CanvasHostState = {
        tabs: [
          {
            id: 'tab-existing',
            artifactId: 'art-1',
            type: 'document',
            title: 'Test',
            isDirty: false,
            openedAt: Date.now(),
          },
        ],
        activeTabId: null,
        artifacts: { 'art-1': artifact },
      };

      const action: TabAction = { type: 'OPEN_TAB', payload: { artifact } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs).toHaveLength(1);
      expect(newState.activeTabId).toBe('tab-existing');
    });

    it('should open multiple tabs for different artifacts', () => {
      const artifact1 = createTestArtifact('art-1', 'Doc 1');
      const artifact2 = createTestArtifact('art-2', 'Doc 2');

      let state = canvasHostReducer(initialCanvasHostState, {
        type: 'OPEN_TAB',
        payload: { artifact: artifact1 },
      });

      state = canvasHostReducer(state, {
        type: 'OPEN_TAB',
        payload: { artifact: artifact2 },
      });

      expect(state.tabs).toHaveLength(2);
      expect(state.tabs[0].artifactId).toBe('art-1');
      expect(state.tabs[1].artifactId).toBe('art-2');
      expect(state.activeTabId).toBe(state.tabs[1].id);
    });
  });

  describe('CLOSE_TAB', () => {
    it('should close a tab and activate the next one', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
          { id: 'tab-2', artifactId: 'art-2', type: 'document', title: 'Doc 2', isDirty: false, openedAt: 2 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'CLOSE_TAB', payload: { tabId: 'tab-1' } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs).toHaveLength(1);
      expect(newState.tabs[0].id).toBe('tab-2');
      expect(newState.activeTabId).toBe('tab-2');
    });

    it('should set activeTabId to null when closing last tab', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'CLOSE_TAB', payload: { tabId: 'tab-1' } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs).toHaveLength(0);
      expect(newState.activeTabId).toBeNull();
    });

    it('should not change state when closing non-existent tab', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'CLOSE_TAB', payload: { tabId: 'non-existent' } };
      const newState = canvasHostReducer(state, action);

      expect(newState).toBe(state);
    });

    it('should select previous tab when closing the last tab in list', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
          { id: 'tab-2', artifactId: 'art-2', type: 'document', title: 'Doc 2', isDirty: false, openedAt: 2 },
          { id: 'tab-3', artifactId: 'art-3', type: 'document', title: 'Doc 3', isDirty: false, openedAt: 3 },
        ],
        activeTabId: 'tab-3',
        artifacts: {},
      };

      const action: TabAction = { type: 'CLOSE_TAB', payload: { tabId: 'tab-3' } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs).toHaveLength(2);
      expect(newState.activeTabId).toBe('tab-2');
    });
  });

  describe('SET_ACTIVE_TAB', () => {
    it('should set the active tab', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
          { id: 'tab-2', artifactId: 'art-2', type: 'document', title: 'Doc 2', isDirty: false, openedAt: 2 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'SET_ACTIVE_TAB', payload: { tabId: 'tab-2' } };
      const newState = canvasHostReducer(state, action);

      expect(newState.activeTabId).toBe('tab-2');
    });

    it('should not change state when setting non-existent tab as active', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'SET_ACTIVE_TAB', payload: { tabId: 'non-existent' } };
      const newState = canvasHostReducer(state, action);

      expect(newState).toBe(state);
    });
  });

  describe('MARK_DIRTY', () => {
    it('should mark a tab as dirty', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: false, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'MARK_DIRTY', payload: { tabId: 'tab-1', isDirty: true } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs[0].isDirty).toBe(true);
    });

    it('should mark a tab as not dirty', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Doc 1', isDirty: true, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'MARK_DIRTY', payload: { tabId: 'tab-1', isDirty: false } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs[0].isDirty).toBe(false);
    });
  });

  describe('UPDATE_TITLE', () => {
    it('should update a tab title', () => {
      const state: CanvasHostState = {
        tabs: [
          { id: 'tab-1', artifactId: 'art-1', type: 'document', title: 'Old Title', isDirty: false, openedAt: 1 },
        ],
        activeTabId: 'tab-1',
        artifacts: {},
      };

      const action: TabAction = { type: 'UPDATE_TITLE', payload: { tabId: 'tab-1', title: 'New Title' } };
      const newState = canvasHostReducer(state, action);

      expect(newState.tabs[0].title).toBe('New Title');
    });
  });
});

describe('CANVAS_TYPE_CONFIGS', () => {
  it('should have config for all canvas types', () => {
    expect(CANVAS_TYPE_CONFIGS.document).toBeDefined();
    expect(CANVAS_TYPE_CONFIGS.tree).toBeDefined();
    expect(CANVAS_TYPE_CONFIGS.timeline).toBeDefined();
    expect(CANVAS_TYPE_CONFIGS.spreadsheet).toBeDefined();
    expect(CANVAS_TYPE_CONFIGS.dashboard).toBeDefined();
  });

  it('should have required properties in each config', () => {
    Object.values(CANVAS_TYPE_CONFIGS).forEach((config) => {
      expect(config.type).toBeDefined();
      expect(config.displayName).toBeDefined();
      expect(config.icon).toBeDefined();
      expect(config.description).toBeDefined();
      expect(config.defaultTitle).toBeDefined();
      expect(typeof config.supportsExport).toBe('boolean');
    });
  });

  it('should have export formats when export is supported', () => {
    Object.values(CANVAS_TYPE_CONFIGS).forEach((config) => {
      if (config.supportsExport) {
        expect(config.exportFormats).toBeDefined();
        expect(config.exportFormats?.length).toBeGreaterThan(0);
      }
    });
  });
});
