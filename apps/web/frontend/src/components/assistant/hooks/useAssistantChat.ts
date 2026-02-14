import { useCallback, useEffect, useRef, useState } from 'react';
import { useAssistantStore } from '@/store/assistant';
import { formatAssistantResponse } from '@/utils/assistantResponses';

interface UseAssistantChatOptions {
  projectId: string | null | undefined;
  onFallbackResponse: (userInput: string) => void;
}

export function useAssistantChat({
  projectId,
  onFallbackResponse,
}: UseAssistantChatOptions) {
  const { addUserMessage, addAssistantMessage, setAiState, setTypingStatus } = useAssistantStore();
  const { aiState } = useAssistantStore();
  const [error, setError] = useState<string | null>(null);
  const inFlightControllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => {
    inFlightControllerRef.current?.abort();
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const messageText = text.trim();
    if (!messageText) return;

    inFlightControllerRef.current?.abort();
    const controller = new AbortController();
    inFlightControllerRef.current = controller;

    addUserMessage(messageText);
    setAiState('thinking');
    setTypingStatus({ detail: 'Reviewing your request…', step: 1, totalSteps: 3 });
    setError(null);

    if (projectId) {
      try {
        setAiState('tool_use');
        setTypingStatus({ detail: 'Querying assistant service…', toolName: 'assistant api', step: 2, totalSteps: 3 });

        const response = await fetch('/api/assistant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            query: messageText,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail ?? 'Unable to send assistant request.');
        }

        const data = await response.json();
        setAiState('streaming');
        setTypingStatus({ detail: 'Aggregating results…', step: 3, totalSteps: 3 });
        addAssistantMessage(formatAssistantResponse(data));
        setAiState('completed');
        setTypingStatus(null);
        return;
      } catch (fetchError) {
        if (controller.signal.aborted) {
          return;
        }

        setError('Unable to reach the assistant service. Showing local suggestions instead.');
        addAssistantMessage(
          'Unable to reach the assistant service. Showing local suggestions instead.',
          undefined,
          true,
          { aiState: 'error' }
        );
        onFallbackResponse(messageText);
        setAiState('error');
        setTypingStatus(null);
        return;
      }
    }

    onFallbackResponse(messageText);
    setAiState('completed');
    setTypingStatus(null);
  }, [addAssistantMessage, addUserMessage, onFallbackResponse, projectId, setAiState, setTypingStatus]);

  return {
    sendMessage,
    error,
    aiState,
  };
}
