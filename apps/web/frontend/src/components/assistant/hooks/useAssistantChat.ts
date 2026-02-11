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
  const { addUserMessage, addAssistantMessage, setAiState } = useAssistantStore();
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
    setError(null);

    if (projectId) {
      try {
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
        addAssistantMessage(formatAssistantResponse(data));
        setAiState('completed');
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
        return;
      }
    }

    onFallbackResponse(messageText);
    setAiState('completed');
  }, [addAssistantMessage, addUserMessage, onFallbackResponse, projectId, setAiState]);

  return {
    sendMessage,
    error,
    aiState,
  };
}
