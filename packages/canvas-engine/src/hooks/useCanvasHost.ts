/**
 * useCanvasHost - Hook for managing canvas host state
 */

import { useReducer, useCallback, useMemo } from 'react';
import type { CanvasArtifact, ArtifactContent } from '../types/artifact';
import {
  canvasHostReducer,
  initialCanvasHostState,
  type CanvasHostState,
  type CanvasTab,
} from '../types/canvas';

export interface UseCanvasHostReturn {
  /** Current state */
  state: CanvasHostState;

  /** Currently open tabs */
  tabs: CanvasTab[];

  /** Currently active tab */
  activeTab: CanvasTab | null;

  /** Currently active artifact */
  activeArtifact: CanvasArtifact | null;

  /** Open a new tab with an artifact */
  openTab: (artifact: CanvasArtifact) => void;

  /** Close a tab by ID */
  closeTab: (tabId: string) => void;

  /** Set the active tab */
  setActiveTab: (tabId: string) => void;

  /** Mark a tab as dirty (has unsaved changes) */
  markDirty: (tabId: string, isDirty: boolean) => void;

  /** Update a tab's title */
  updateTitle: (tabId: string, title: string) => void;

  /** Update an artifact's content */
  updateArtifactContent: <T extends ArtifactContent>(
    artifactId: string,
    content: T
  ) => void;

  /** Get an artifact by ID */
  getArtifact: (artifactId: string) => CanvasArtifact | undefined;

  /** Check if a tab is dirty */
  isTabDirty: (tabId: string) => boolean;
}

export function useCanvasHost(
  initialState: CanvasHostState = initialCanvasHostState
): UseCanvasHostReturn {
  const [state, dispatch] = useReducer(canvasHostReducer, initialState);

  const openTab = useCallback((artifact: CanvasArtifact) => {
    dispatch({ type: 'OPEN_TAB', payload: { artifact } });
  }, []);

  const closeTab = useCallback((tabId: string) => {
    dispatch({ type: 'CLOSE_TAB', payload: { tabId } });
  }, []);

  const setActiveTab = useCallback((tabId: string) => {
    dispatch({ type: 'SET_ACTIVE_TAB', payload: { tabId } });
  }, []);

  const markDirty = useCallback((tabId: string, isDirty: boolean) => {
    dispatch({ type: 'MARK_DIRTY', payload: { tabId, isDirty } });
  }, []);

  const updateTitle = useCallback((tabId: string, title: string) => {
    dispatch({ type: 'UPDATE_TITLE', payload: { tabId, title } });
  }, []);

  // This action type is not in reducer, so we handle it separately
  // In a real app, this would likely be a separate action or use immer
  const updateArtifactContent = useCallback(
    <T extends ArtifactContent>(artifactId: string, content: T) => {
      // For now, we'll need to extend the reducer or use a separate mechanism
      // This is a placeholder that logs the update
      console.log('Updating artifact content:', artifactId, content);
    },
    []
  );

  const getArtifact = useCallback(
    (artifactId: string) => state.artifacts[artifactId],
    [state.artifacts]
  );

  const isTabDirty = useCallback(
    (tabId: string) => {
      const tab = state.tabs.find(t => t.id === tabId);
      return tab?.isDirty ?? false;
    },
    [state.tabs]
  );

  const activeTab = useMemo(
    () => state.tabs.find(t => t.id === state.activeTabId) ?? null,
    [state.tabs, state.activeTabId]
  );

  const activeArtifact = useMemo(
    () => (activeTab ? state.artifacts[activeTab.artifactId] ?? null : null),
    [activeTab, state.artifacts]
  );

  return {
    state,
    tabs: state.tabs,
    activeTab,
    activeArtifact,
    openTab,
    closeTab,
    setActiveTab,
    markDirty,
    updateTitle,
    updateArtifactContent,
    getArtifact,
    isTabDirty,
  };
}
