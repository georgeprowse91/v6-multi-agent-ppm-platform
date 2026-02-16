import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useAssistantStore, type ActionChip } from '@/store/assistant';
import { useIntakeAssistantStore } from '@/store/assistant/useIntakeAssistantStore';

interface IntakeAssistantResponse {
  step_id: string;
  questions: string[];
  proposals: Record<string, string>;
  apply_hints: string[];
}

function toApplyChip(field: string, value: string): ActionChip {
  return {
    id: `intake-apply-${field}`,
    label: `Apply ${field}`,
    category: 'create',
    priority: 'high',
    actionType: 'custom',
    payload: {
      type: 'custom',
      actionKey: 'intake_apply_field',
      data: { field, value },
    },
    enabled: true,
    description: `Apply proposed value to ${field}`,
  };
}

export function useIntakeAssistantAdapter(active: boolean) {
  const { context } = useIntakeAssistantStore();
  const { addAssistantMessage, setAiState, setTypingStatus } = useAssistantStore();
  const lastContextSignature = useRef<string | null>(null);

  const contextSignature = useMemo(() => {
    if (!active || !context) return null;
    return JSON.stringify(context);
  }, [active, context]);

  const fetchGuidance = useCallback(
    async (answer?: string) => {
      if (!active || !context) return;
      setAiState('thinking');
      setTypingStatus({ detail: 'Preparing intake guidance…', step: 1, totalSteps: 2 });

      const response = await fetch('/v1/api/intake/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_id: context.stepId,
          step_index: context.stepIndex,
          form_state: context.formState,
          validation_errors: context.errors,
          user_answer: answer,
        }),
      });

      if (!response.ok) {
        throw new Error('Unable to load intake assistant guidance.');
      }

      const payload = (await response.json()) as IntakeAssistantResponse;
      const proposals = Object.entries(payload.proposals ?? {});
      const chips = proposals.map(([field, value]) => toApplyChip(field, value));

      const questionBlock = payload.questions.length
        ? `Questions to clarify:\n${payload.questions.map((question) => `- ${question}`).join('\n')}`
        : 'No clarifying questions for this step.';
      const proposalBlock = proposals.length
        ? `Proposals:\n${proposals.map(([field, value]) => `- ${field}: ${value}`).join('\n')}`
        : 'No proposals yet.';
      const hintsBlock = payload.apply_hints.length
        ? `Apply hints:\n${payload.apply_hints.map((hint) => `- ${hint}`).join('\n')}`
        : '';

      addAssistantMessage(
        [questionBlock, proposalBlock, hintsBlock].filter(Boolean).join('\n\n'),
        chips
      );
      setAiState('completed');
      setTypingStatus(null);
    },
    [active, addAssistantMessage, context, setAiState, setTypingStatus]
  );

  useEffect(() => {
    if (!active || !contextSignature || contextSignature === lastContextSignature.current) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchGuidance().catch((error) => {
        addAssistantMessage(error instanceof Error ? error.message : 'Unable to load intake guidance.', undefined, true, { aiState: 'error' });
        setAiState('error');
        setTypingStatus(null);
      });
      lastContextSignature.current = contextSignature;
    }, 500);

    return () => window.clearTimeout(timeoutId);
  }, [active, addAssistantMessage, contextSignature, fetchGuidance, setAiState, setTypingStatus]);

  const sendIntakeMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      useAssistantStore.getState().addUserMessage(trimmed);
      try {
        await fetchGuidance(trimmed);
      } catch (error) {
        addAssistantMessage(error instanceof Error ? error.message : 'Unable to load intake guidance.', undefined, true, { aiState: 'error' });
        setAiState('error');
        setTypingStatus(null);
      }
    },
    [addAssistantMessage, fetchGuidance, setAiState, setTypingStatus]
  );

  return { sendIntakeMessage };
}
