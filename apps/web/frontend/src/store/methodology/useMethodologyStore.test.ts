import { describe, expect, it, beforeEach, vi, afterEach } from 'vitest';
import { useMethodologyStore } from './useMethodologyStore';
import type {
  MethodologyActivity,
  MethodologyStage,
  MethodologyStatus,
  ProjectMethodology,
} from './types';

// Mock the API client used by hydrateFromWorkspace, resolveNodeRuntime, etc.
vi.mock('@/services/apiClient', () => ({
  requestJson: vi.fn(),
}));

// Mock the assistant store (used by error paths to send messages)
vi.mock('@/store/assistant', () => ({
  useAssistantStore: {
    getState: () => ({
      addAssistantMessage: vi.fn(),
    }),
  },
}));

import { requestJson } from '@/services/apiClient';

/** Helper: build a MethodologyActivity */
function makeActivity(overrides: Partial<MethodologyActivity> = {}): MethodologyActivity {
  return {
    id: 'activity-1',
    name: 'Test Activity',
    description: 'A test activity',
    status: 'not_started',
    canvasType: 'document',
    prerequisites: [],
    order: 1,
    ...overrides,
  };
}

/** Helper: build a MethodologyStage */
function makeStage(overrides: Partial<MethodologyStage> = {}): MethodologyStage {
  return {
    id: 'stage-1',
    name: 'Test Stage',
    status: 'not_started',
    activities: [makeActivity()],
    prerequisites: [],
    order: 1,
    ...overrides,
  };
}

/** Helper: build a ProjectMethodology */
function makeProjectMethodology(overrides: Partial<ProjectMethodology> = {}): ProjectMethodology {
  return {
    projectId: 'proj-test',
    projectName: 'Test Project',
    methodology: {
      id: 'predictive',
      name: 'Predictive',
      description: 'Test methodology',
      type: 'predictive',
      version: '1.0',
      stages: [
        makeStage({
          id: 'stage-initiation',
          name: 'Initiation',
          order: 1,
          prerequisites: [],
          activities: [
            makeActivity({ id: 'act-charter', name: 'Project Charter', order: 1, prerequisites: [] }),
            makeActivity({ id: 'act-stakeholders', name: 'Stakeholder Analysis', order: 2, prerequisites: ['act-charter'] }),
          ],
        }),
        makeStage({
          id: 'stage-planning',
          name: 'Planning',
          order: 2,
          prerequisites: ['stage-initiation'],
          activities: [
            makeActivity({ id: 'act-scope', name: 'Scope Definition', order: 1, prerequisites: [] }),
          ],
        }),
      ],
      monitoring: [
        makeActivity({
          id: 'mon-dashboard',
          name: 'Project Dashboard',
          canvasType: 'dashboard',
          alwaysAccessible: true,
        }),
      ],
    },
    currentActivityId: null,
    expandedStageIds: ['stage-initiation'],
    ...overrides,
  };
}

describe('useMethodologyStore', () => {
  beforeEach(() => {
    // Reset store data - do NOT use replace (true) which strips action functions
    const methodology = makeProjectMethodology();
    useMethodologyStore.setState({
      projectMethodology: methodology,
      availableMethodologies: ['predictive', 'adaptive', 'hybrid'],
      isHydrating: false,
      templatesAvailableHere: [],
      templatesRequiredHere: [],
      templatesInReview: [],
      runtimeActionsAvailable: [],
      runtimeDefaultViewContract: null,
      backendReachable: true,
      reviewQueue: [],
      currentActivityId: null,
      expandedStageIds: ['stage-initiation'],
    });
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('should have a projectMethodology', () => {
      const state = useMethodologyStore.getState();
      expect(state.projectMethodology).toBeDefined();
      expect(state.projectMethodology.methodology.id).toBe('predictive');
    });

    it('should not be hydrating', () => {
      expect(useMethodologyStore.getState().isHydrating).toBe(false);
    });

    it('should have available methodologies', () => {
      expect(useMethodologyStore.getState().availableMethodologies).toEqual([
        'predictive',
        'adaptive',
        'hybrid',
      ]);
    });

    it('should have no current activity', () => {
      expect(useMethodologyStore.getState().currentActivityId).toBeNull();
    });

    it('should have first stage expanded', () => {
      expect(useMethodologyStore.getState().expandedStageIds).toContain('stage-initiation');
    });

    it('should have backendReachable as true', () => {
      expect(useMethodologyStore.getState().backendReachable).toBe(true);
    });
  });

  describe('navigation actions', () => {
    it('should set current activity', () => {
      useMethodologyStore.getState().setCurrentActivity('act-charter');

      const state = useMethodologyStore.getState();
      expect(state.currentActivityId).toBe('act-charter');
      expect(state.projectMethodology.currentActivityId).toBe('act-charter');
    });

    it('should clear current activity when set to null', () => {
      useMethodologyStore.getState().setCurrentActivity('act-charter');
      useMethodologyStore.getState().setCurrentActivity(null);

      expect(useMethodologyStore.getState().currentActivityId).toBeNull();
    });

    it('should toggle stage expanded', () => {
      // stage-initiation is already expanded
      useMethodologyStore.getState().toggleStageExpanded('stage-initiation');
      expect(useMethodologyStore.getState().expandedStageIds).not.toContain('stage-initiation');

      useMethodologyStore.getState().toggleStageExpanded('stage-initiation');
      expect(useMethodologyStore.getState().expandedStageIds).toContain('stage-initiation');
    });

    it('should expand a stage', () => {
      useMethodologyStore.getState().expandStage('stage-planning');
      expect(useMethodologyStore.getState().expandedStageIds).toContain('stage-planning');
    });

    it('should not duplicate expanded stage ID', () => {
      useMethodologyStore.getState().expandStage('stage-initiation');
      const count = useMethodologyStore.getState().expandedStageIds.filter(
        (id) => id === 'stage-initiation'
      ).length;
      expect(count).toBe(1);
    });

    it('should collapse a stage', () => {
      useMethodologyStore.getState().collapseStage('stage-initiation');
      expect(useMethodologyStore.getState().expandedStageIds).not.toContain('stage-initiation');
    });

    it('should expand all stages', () => {
      useMethodologyStore.getState().expandAllStages();
      const expanded = useMethodologyStore.getState().expandedStageIds;
      expect(expanded).toContain('stage-initiation');
      expect(expanded).toContain('stage-planning');
    });

    it('should collapse all stages', () => {
      useMethodologyStore.getState().expandAllStages();
      useMethodologyStore.getState().collapseAllStages();
      expect(useMethodologyStore.getState().expandedStageIds).toEqual([]);
    });
  });

  describe('status update actions', () => {
    it('should update activity status', () => {
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');

      const activity = useMethodologyStore.getState().getActivity('act-charter');
      expect(activity?.status).toBe('complete');
    });

    it('should recompute stage status when activity changes', () => {
      // Mark one activity complete - stage should become in_progress
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');

      const stage = useMethodologyStore.getState().getStage('stage-initiation');
      expect(stage?.status).toBe('in_progress');
    });

    it('should update stage status directly', () => {
      useMethodologyStore.getState().updateStageStatus('stage-initiation', 'blocked');

      const stage = useMethodologyStore.getState().getStage('stage-initiation');
      expect(stage?.status).toBe('blocked');
    });
  });

  describe('selectors', () => {
    it('getStage should return a stage by ID', () => {
      const stage = useMethodologyStore.getState().getStage('stage-initiation');
      expect(stage?.name).toBe('Initiation');
    });

    it('getStage should return undefined for nonexistent stage', () => {
      expect(useMethodologyStore.getState().getStage('nonexistent')).toBeUndefined();
    });

    it('getActivity should return an activity by ID', () => {
      const activity = useMethodologyStore.getState().getActivity('act-charter');
      expect(activity?.name).toBe('Project Charter');
    });

    it('getActivity should return a monitoring activity', () => {
      const activity = useMethodologyStore.getState().getActivity('mon-dashboard');
      expect(activity?.name).toBe('Project Dashboard');
    });

    it('getActivity should return undefined for nonexistent activity', () => {
      expect(useMethodologyStore.getState().getActivity('nonexistent')).toBeUndefined();
    });

    it('getCurrentActivity should return null when no activity is selected', () => {
      expect(useMethodologyStore.getState().getCurrentActivity()).toBeNull();
    });

    it('getCurrentActivity should return the current activity', () => {
      useMethodologyStore.getState().setCurrentActivity('act-charter');
      const current = useMethodologyStore.getState().getCurrentActivity();
      expect(current?.id).toBe('act-charter');
    });

    it('getStageForActivity should find the stage containing an activity', () => {
      const stage = useMethodologyStore.getState().getStageForActivity('act-charter');
      expect(stage?.id).toBe('stage-initiation');
    });

    it('getStageForActivity should return a synthetic stage for monitoring activities', () => {
      const stage = useMethodologyStore.getState().getStageForActivity('mon-dashboard');
      expect(stage?.id).toBe('monitoring');
      expect(stage?.name).toBe('Monitoring & Controlling');
      expect(stage?.alwaysAccessible).toBe(true);
    });

    it('getStageForActivity should return undefined for nonexistent activity', () => {
      expect(useMethodologyStore.getState().getStageForActivity('nonexistent')).toBeUndefined();
    });

    it('getAllActivities should return all activities including monitoring', () => {
      const all = useMethodologyStore.getState().getAllActivities();
      const ids = all.map((a) => a.id);
      expect(ids).toContain('act-charter');
      expect(ids).toContain('act-stakeholders');
      expect(ids).toContain('act-scope');
      expect(ids).toContain('mon-dashboard');
    });
  });

  describe('computed lock state', () => {
    it('isStageLockedComputed should return false for first stage (no prerequisites)', () => {
      expect(useMethodologyStore.getState().isStageLockedComputed('stage-initiation')).toBe(false);
    });

    it('isStageLockedComputed should return true for stage with incomplete prerequisite stage', () => {
      // stage-planning requires stage-initiation to be complete
      expect(useMethodologyStore.getState().isStageLockedComputed('stage-planning')).toBe(true);
    });

    it('isStageLockedComputed should return false after prerequisite stage is complete', () => {
      // Mark all initiation activities complete
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');
      useMethodologyStore.getState().updateActivityStatus('act-stakeholders', 'complete');

      expect(useMethodologyStore.getState().isStageLockedComputed('stage-planning')).toBe(false);
    });

    it('isActivityLockedComputed should return false for activity with no prerequisites', () => {
      expect(useMethodologyStore.getState().isActivityLockedComputed('act-charter')).toBe(false);
    });

    it('isActivityLockedComputed should return true for activity with incomplete prerequisites', () => {
      // act-stakeholders requires act-charter
      // Stage is not locked (stage-initiation has no prereqs), but the activity has a prereq
      expect(useMethodologyStore.getState().isActivityLockedComputed('act-stakeholders')).toBe(true);
    });

    it('isActivityLockedComputed should return false after prerequisite is complete', () => {
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');
      expect(useMethodologyStore.getState().isActivityLockedComputed('act-stakeholders')).toBe(false);
    });

    it('isStageLockedComputed should return false for unknown stage', () => {
      expect(useMethodologyStore.getState().isStageLockedComputed('nonexistent')).toBe(false);
    });
  });

  describe('getStageProgressComputed', () => {
    it('should return 0 for a stage with no complete activities', () => {
      expect(useMethodologyStore.getState().getStageProgressComputed('stage-initiation')).toBe(0);
    });

    it('should return 50 when half activities are complete', () => {
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');
      // 1 of 2 complete => 50%
      expect(useMethodologyStore.getState().getStageProgressComputed('stage-initiation')).toBe(50);
    });

    it('should return 100 when all activities are complete', () => {
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'complete');
      useMethodologyStore.getState().updateActivityStatus('act-stakeholders', 'complete');
      expect(useMethodologyStore.getState().getStageProgressComputed('stage-initiation')).toBe(100);
    });

    it('should count in_progress as 50% done', () => {
      useMethodologyStore.getState().updateActivityStatus('act-charter', 'in_progress');
      // 0.5 of 2 => 25%
      expect(useMethodologyStore.getState().getStageProgressComputed('stage-initiation')).toBe(25);
    });

    it('should return 0 for nonexistent stage', () => {
      expect(useMethodologyStore.getState().getStageProgressComputed('nonexistent')).toBe(0);
    });
  });

  describe('loadProjectMethodology', () => {
    it('should replace the project methodology', () => {
      const newMethodology = makeProjectMethodology({
        projectId: 'new-proj',
        projectName: 'New Project',
        currentActivityId: 'act-scope',
        expandedStageIds: ['stage-planning'],
      });

      useMethodologyStore.getState().loadProjectMethodology(newMethodology);

      const state = useMethodologyStore.getState();
      expect(state.projectMethodology.projectId).toBe('new-proj');
      expect(state.currentActivityId).toBe('act-scope');
      expect(state.expandedStageIds).toEqual(['stage-planning']);
    });
  });

  describe('createFromTemplate', () => {
    it('should create a fallback methodology and mark backend unreachable', () => {
      useMethodologyStore.getState().createFromTemplate('template-1', 'proj-new', 'New Project');

      const state = useMethodologyStore.getState();
      expect(state.projectMethodology.projectId).toBe('proj-new');
      expect(state.projectMethodology.projectName).toBe('New Project');
      expect(state.backendReachable).toBe(false);
      expect(state.currentActivityId).toBeNull();
      expect(state.expandedStageIds).toEqual([]);
    });
  });

  describe('hydrateFromWorkspace', () => {
    it('should set isHydrating during hydration', async () => {
      const workspacePayload = {
        project_id: 'proj-test',
        methodology: 'predictive',
        current_activity_id: null,
        available_methodologies: ['predictive'],
        methodology_map_summary: {
          id: 'predictive',
          name: 'Predictive',
          description: 'Test',
          stages: [
            {
              id: 'stage-1',
              name: 'Stage 1',
              activities: [
                {
                  id: 'act-1',
                  name: 'Activity 1',
                  description: 'desc',
                  prerequisites: [],
                  category: 'test',
                  recommended_canvas_tab: 'document',
                  assistant_prompts: [],
                  access: { allowed: true },
                  completed: false,
                },
              ],
            },
          ],
        },
      };

      vi.mocked(requestJson).mockResolvedValue(workspacePayload);

      const promise = useMethodologyStore.getState().hydrateFromWorkspace('proj-test');
      expect(useMethodologyStore.getState().isHydrating).toBe(true);

      await promise;
      expect(useMethodologyStore.getState().isHydrating).toBe(false);
      expect(useMethodologyStore.getState().backendReachable).toBe(true);
    });

    it('should fall back to emergency methodology on error', async () => {
      vi.mocked(requestJson).mockRejectedValue(new Error('API unavailable'));

      await useMethodologyStore.getState().hydrateFromWorkspace('proj-test');

      const state = useMethodologyStore.getState();
      expect(state.isHydrating).toBe(false);
      expect(state.backendReachable).toBe(false);
      expect(state.projectMethodology.methodology.id).toBe('unavailable');
    });

    it('should populate methodology stages from workspace response', async () => {
      const workspacePayload = {
        project_id: 'proj-1',
        methodology: 'predictive',
        current_activity_id: 'act-intake',
        available_methodologies: ['predictive', 'adaptive'],
        methodology_map_summary: {
          id: 'predictive',
          name: 'Predictive PMBOK',
          description: 'Full lifecycle',
          stages: [
            {
              id: 'stage-intake',
              name: 'Intake',
              activities: [
                {
                  id: 'act-intake',
                  name: 'Intake Review',
                  description: 'Review intake',
                  prerequisites: [],
                  category: 'intake',
                  recommended_canvas_tab: 'document',
                  assistant_prompts: ['Review this'],
                  access: { allowed: true },
                  completed: true,
                },
              ],
            },
          ],
          monitoring: [],
        },
      };

      vi.mocked(requestJson).mockResolvedValue(workspacePayload);

      await useMethodologyStore.getState().hydrateFromWorkspace('proj-1');

      const state = useMethodologyStore.getState();
      expect(state.projectMethodology.methodology.name).toBe('Predictive PMBOK');
      expect(state.projectMethodology.methodology.stages.length).toBe(1);
      expect(state.projectMethodology.methodology.stages[0].id).toBe('stage-intake');
      expect(state.currentActivityId).toBe('act-intake');
      expect(state.availableMethodologies).toEqual(['predictive', 'adaptive']);

      const activity = state.getActivity('act-intake');
      expect(activity?.status).toBe('complete');
    });
  });
});
