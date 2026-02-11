import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantPanel } from './AssistantPanel';
import { useAssistantStore } from '@/store/assistant';
import { useMethodologyStore } from '@/store/methodology';

const mockFetch = () =>
  vi.fn(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({ suggestions: [], context: {}, generated_by: 'test' }),
        { status: 200 }
      )
    )
  );

describe('AssistantPanel quick actions', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(mockFetch());
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      value: vi.fn(),
      writable: true,
    });
    useMethodologyStore.getState().setCurrentActivity('act-charter');
  });

  afterEach(() => {
    useAssistantStore.setState({
      messages: [],
      actionChips: [],
      context: null,
      isGeneratingSuggestions: false,
    });
    vi.restoreAllMocks();
  });

  it('renders quick actions when assistant store has chips', async () => {
    useAssistantStore.setState({
      actionChips: [
        {
          id: 'qa-1',
          label: 'Open Charter',
          category: 'navigate',
          priority: 'high',
          actionType: 'open_activity',
          payload: { type: 'open_activity', activityId: 'act-charter' },
          enabled: true,
        },
      ],
    });

    render(<AssistantPanel />);

    await waitFor(() => {
      expect(useAssistantStore.getState().isGeneratingSuggestions).toBe(false);
    });

    expect(screen.getByRole('button', { name: /open charter/i })).toBeInTheDocument();
    expect(screen.queryByText(/suggested actions/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/next actions/i)).not.toBeInTheDocument();
  });
});
