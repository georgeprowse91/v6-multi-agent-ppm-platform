import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantPanel } from './AssistantPanel';
import { useAssistantStore } from '@/store/assistant';
import { useMethodologyStore } from '@/store/methodology';

const conversationPayload = {
  scenario: 'project_intake',
  messages: [
    { role: 'assistant', content: 'Welcome to the Project Intake demo. What initiative would you like to submit today?' },
    { role: 'user', content: 'I need to launch a customer self-service portal.' },
    { role: 'assistant', content: 'Great. What outcome should this portal improve first: support ticket deflection or faster onboarding?' },
    { role: 'user', content: 'Support ticket deflection.' },
    { role: 'assistant', content: 'Understood. I captured the objective as reducing support ticket volume by 20% in two quarters. Do you want me to draft an intake summary now?' },
  ],
};

describe('AssistantPanel demo mode', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/assistant/demo-conversations/')) {
        return Promise.resolve(new Response(JSON.stringify(conversationPayload), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ suggestions: [], context: {}, generated_by: 'test' }), { status: 200 }));
    });

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
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('shows scripted demo controls and advances through scripted steps', async () => {
    render(
      <MemoryRouter>
        <AssistantPanel />
      </MemoryRouter>
    );

    await screen.findByText(/scripted demo mode/i);
    await screen.findByText(/welcome to the project intake demo/i);

    const input = screen.getByLabelText(/ai assistant chat input/i);
    fireEvent.change(input, { target: { value: 'I need to launch a customer self-service portal.' } });
    fireEvent.submit(input.closest('form')!);

    await screen.findByText(/support ticket deflection or faster onboarding/i);

    fireEvent.change(input, { target: { value: 'faster onboarding' } });
    fireEvent.submit(input.closest('form')!);

    await screen.findByText(/cutting onboarding cycle time by 30%/i);
  });

  it('restarts the current scenario', async () => {
    render(
      <MemoryRouter>
        <AssistantPanel />
      </MemoryRouter>
    );
    await screen.findByText(/welcome to the project intake demo/i);

    const input = screen.getByLabelText(/ai assistant chat input/i);
    fireEvent.change(input, { target: { value: 'I need to launch a customer self-service portal.' } });
    fireEvent.submit(input.closest('form')!);
    await screen.findByText(/support ticket deflection or faster onboarding/i);

    fireEvent.click(screen.getByRole('button', { name: /restart/i }));

    await waitFor(() => {
      const welcomeMessages = screen.getAllByText(/welcome to the project intake demo/i);
      expect(welcomeMessages.length).toBeGreaterThan(0);
    });
  });
});
