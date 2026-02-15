import { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { createArtifact, createEmptyContent, type CanvasType } from '@ppm/canvas-engine';
import { requestJson } from '@/services/apiClient';
import { useAssistantStore } from '@/store/assistant';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useMethodologyStore } from '@/store/methodology';
import { MethodologyMapCanvas } from './MethodologyMapCanvas';
import { ActivityDetailPanel } from './ActivityDetailPanel';

const canvasMap: Record<string, CanvasType> = {
  document: 'document', spreadsheet: 'spreadsheet', timeline: 'timeline', dashboard: 'dashboard', kanban: 'tree', risk_log: 'spreadsheet', decision_log: 'document', form: 'document', whiteboard: 'document',
};

export function MethodologyWorkspaceSurface() {
  const {
    projectMethodology,
    currentActivityId,
    setCurrentActivity,
    getActivity,
    getStageForActivity,
    getAllActivities,
    isStageLockedComputed,
    isActivityLockedComputed,
    resolveNodeRuntime,
    executeNodeAction,
    runtimeActionsAvailable,
    runtimeDefaultViewContract,
    templatesRequiredHere,
    templatesInReview,
    backendReachable,
  } = useMethodologyStore();
  const { openArtifact } = useCanvasStore();
  const navigate = useNavigate();
  const { setActionChips, addAssistantMessage } = useAssistantStore();

  const selectedActivity = currentActivityId ? getActivity(currentActivityId) ?? null : null;
  const selectedStage = currentActivityId ? getStageForActivity(currentActivityId) : undefined;

  const prerequisiteNames = useMemo(() => {
    if (!selectedActivity) return [];
    const all = getAllActivities();
    return selectedActivity.prerequisites
      .map((id) => all.find((activity) => activity.id === id))
      .filter((activity) => activity && activity.status !== 'complete')
      .map((activity) => activity!.name);
  }, [getAllActivities, selectedActivity]);

  const publishAssistantContext = useCallback((activityId: string, stageId: string) => {
    const activity = getActivity(activityId);
    if (!activity) return;
    setActionChips(runtimeActionsAvailable
      .filter((event) => ['generate', 'update', 'review', 'approve', 'publish'].includes(event))
      .map((event) => ({
        id: `runtime-${event}`,
        label: event[0].toUpperCase() + event.slice(1),
        category: 'navigate',
        priority: 'high',
        actionType: 'custom',
        payload: { type: 'custom', actionKey: 'methodology_runtime_action', data: { lifecycleEvent: event, stageId, activityId } },
        enabled: true,
      })));
    addAssistantMessage(`Context set: ${activity.name}. Status: ${activity.status.replace('_', ' ')}.`);
  }, [addAssistantMessage, getActivity, runtimeActionsAvailable, setActionChips]);

  const selectActivity = useCallback(async (activityId: string, stageId: string) => {
    setCurrentActivity(activityId);
    await requestJson(`/api/workspace/${encodeURIComponent(projectMethodology.projectId)}/select`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_stage_id: stageId === 'monitoring' ? null : stageId, current_activity_id: activityId }),
    });
    await resolveNodeRuntime({ methodologyId: projectMethodology.methodology.id, stageId, activityId, event: 'view' });
    publishAssistantContext(activityId, stageId);
    const selected = getActivity(activityId);
    const isMonitoringDashboard =
      stageId === 'monitoring' &&
      ((selected?.name ?? '').toLowerCase().includes('dashboard') || (selected?.name ?? '').toLowerCase().includes('performance'));
    if (isMonitoringDashboard) {
      navigate(`/projects/${encodeURIComponent(projectMethodology.projectId)}/performance-dashboard`);
    }
  }, [getActivity, navigate, projectMethodology.methodology.id, projectMethodology.projectId, publishAssistantContext, resolveNodeRuntime, setCurrentActivity]);

  const runLifecycleAction = useCallback(async (event: 'generate' | 'update' | 'review' | 'approve' | 'publish') => {
    if (!selectedActivity) return;
    if (!backendReachable) {
      addAssistantMessage('Backend unavailable. Runtime actions are disabled until connectivity is restored.');
      return;
    }
    const stageId = selectedStage?.id ?? 'monitoring';
    const response = await executeNodeAction({
      workspaceId: projectMethodology.projectId,
      methodologyId: projectMethodology.methodology.id,
      stageId,
      activityId: selectedActivity.id,
      lifecycleEvent: event,
    });

    if (response.human_review?.required) {
      addAssistantMessage('Action submitted and pending human review.');
      return;
    }

    const contract = await resolveNodeRuntime({ methodologyId: projectMethodology.methodology.id, stageId, activityId: selectedActivity.id, event: 'view' });
    const runtimeCanvasType = contract?.canvas?.canvas_type ?? runtimeDefaultViewContract?.canvas?.canvas_type ?? selectedActivity.canvasType;
    const canvasType = (canvasMap[runtimeCanvasType] ?? selectedActivity.canvasType) as CanvasType;
    openArtifact(createArtifact(canvasType, selectedActivity.name, projectMethodology.projectId, createEmptyContent(canvasType)));
  }, [addAssistantMessage, backendReachable, executeNodeAction, openArtifact, projectMethodology.methodology.id, projectMethodology.projectId, resolveNodeRuntime, runtimeDefaultViewContract?.canvas?.canvas_type, selectedActivity, selectedStage?.id]);

  if (!selectedActivity) {
    return (
      <>
        {!backendReachable && (
          <div role="alert">Backend unavailable. Methodology is in read-only emergency mode.</div>
        )}
      <MethodologyMapCanvas
        stages={projectMethodology.methodology.stages}
        monitoring={projectMethodology.methodology.monitoring}
        currentActivityId={currentActivityId}
        isStageLockedComputed={isStageLockedComputed}
        isActivityLockedComputed={isActivityLockedComputed}
        templatesRequiredHere={templatesRequiredHere}
        templatesInReview={templatesInReview}
        onSelectActivity={(activity, stageId) => { void selectActivity(activity.id, stageId); }}
      />
      </>
    );
  }

  return (
    <>
      {!backendReachable && (
        <div role="alert">Backend unavailable. Runtime actions are disabled.</div>
      )}
    <ActivityDetailPanel
      activity={selectedActivity}
      stageLabel={selectedStage?.id === 'monitoring' ? 'Monitoring & Controlling' : (selectedStage?.name ?? 'Monitoring & Controlling')}
      isLocked={isActivityLockedComputed(selectedActivity.id)}
      missingPrerequisites={prerequisiteNames}
      runtimeActionsAvailable={runtimeActionsAvailable}
      onLifecycleAction={(event) => { void runLifecycleAction(event); }}
      actionsDisabled={!backendReachable}
    />
    </>
  );
}
