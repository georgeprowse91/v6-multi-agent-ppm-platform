import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantPanel } from './AssistantPanel';
import { useAssistantStore } from '@/store/assistant';
import { useMethodologyStore } from '@/store/methodology';

const stubFetch = () =>
  vi.fn(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({ suggestions: [], context: {}, generated_by: 'test' }),
        { status: 200 }
      )
    )
  );

describe('AssistantPanel prompt library', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', stubFetch());
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
    vi.unstubAllGlobals();
  });

  it('renders prompt chips for the current stage', async () => {
    render(<AssistantPanel />);

    await waitFor(() => {
      expect(useAssistantStore.getState().isGeneratingSuggestions).toBe(false);
    });

    expect(
      await screen.findByRole('button', { name: /Generate project charter/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Generate work breakdown structure/i })
    ).not.toBeInTheDocument();
  });

  it('inserts prompt description into the input when clicked', async () => {
    render(<AssistantPanel />);

    await waitFor(() => {
      expect(useAssistantStore.getState().isGeneratingSuggestions).toBe(false);
    });

    const promptButton = await screen.findByRole('button', {
      name: /Generate project charter/i,
    });
    fireEvent.click(promptButton);

    const input = screen.getByPlaceholderText('Ask about your project...');
    expect((input as HTMLInputElement).value).toContain(
      'write a complete project charter'
    );
  });
});
