import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantPanel } from '@/components/assistant/AssistantPanel';
import HomePage from '@/pages/HomePage';
import IntakeFormPage from '@/pages/IntakeFormPage';
import { useAppStore } from '@/store';
import { useAssistantStore } from '@/store/assistant';
import { useIntakeAssistantStore } from '@/store/assistant/useIntakeAssistantStore';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/"
          element={(
            <>
              <HomePage />
              <AssistantPanel />
            </>
          )}
        />
        <Route
          path="/intake/new"
          element={(
            <>
              <IntakeFormPage />
              <AssistantPanel />
            </>
          )}
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('Intake assistant regression coverage', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      value: vi.fn(),
      writable: true,
    });

    useAppStore.setState({ rightPanelCollapsed: false });
  });

  afterEach(() => {
    useAssistantStore.setState({
      messages: [],
      actionChips: [],
      context: null,
      mode: 'entry',
      aiState: 'idle',
      typingStatus: null,
      isGeneratingSuggestions: false,
    });
    useIntakeAssistantStore.getState().clearContext();
    vi.restoreAllMocks();
  });

  it('renders assistant on entry route with 4 chips and navigates to intake from Log new intake', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ suggestions: [], context: {}, generated_by: 'test' }), { status: 200 })
    );

    renderAt('/');

    expect(await screen.findByRole('heading', { name: 'Assistant' })).toBeInTheDocument();
    await waitFor(() => {
      expect(useAssistantStore.getState().actionChips).toHaveLength(4);
    });
    expect((await screen.findAllByRole('button', { name: /log new intake/i })).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /show 1 more quick actions/i })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: /log new intake/i })[0]!);

    expect(await screen.findByRole('heading', { name: /portfolio intake request/i })).toBeInTheDocument();
  });

  it('applies intake assistant proposals and asks overwrite confirmation for non-empty fields', async () => {
    const assistantResponses = [
      {
        step_id: 'business',
        questions: ['Can you confirm expected outcomes?'],
        proposals: {
          expectedBenefits: 'Reduce manual effort by 20%.',
          successMetrics: 'Improve SLA adherence to 95%.',
        },
        apply_hints: [
          'expectedBenefits: safe to apply directly (field is empty).',
          'successMetrics: safe to apply directly (field is empty).',
        ],
      },
      {
        step_id: 'business',
        questions: [],
        proposals: {
          expectedBenefits: 'New expected benefit proposal.',
        },
        apply_hints: ['expectedBenefits: confirmation required because the field already contains a value.'],
      },
    ];

    vi.spyOn(window, 'confirm').mockReturnValue(false);

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/v1/api/intake/assistant')) {
        const payload = assistantResponses.shift() ?? assistantResponses[0];
        return new Response(JSON.stringify(payload), { status: 200 });
      }
      return new Response(JSON.stringify({ suggestions: [], context: {}, generated_by: 'test' }), { status: 200 });
    });

    renderAt('/intake/new');
    await waitFor(() => {
      expect(useIntakeAssistantStore.getState().context).not.toBeNull();
    });

    const input = await screen.findByLabelText(/ai assistant chat input/i);
    fireEvent.change(input, { target: { value: 'propose updates' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/v1/api/intake/assistant',
        expect.objectContaining({ method: 'POST' })
      );
    });

    await waitFor(() => {
      expect(useAssistantStore.getState().actionChips.map((chip) => chip.label)).toEqual(
        expect.arrayContaining(['Apply expectedBenefits', 'Apply successMetrics'])
      );
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'Apply expectedBenefits' })[0]!);
    fireEvent.click(screen.getAllByRole('button', { name: 'Apply successMetrics' })[0]!);

    fireEvent.change(screen.getByLabelText(/sponsor name/i), { target: { value: 'Alex' } });
    fireEvent.change(screen.getByLabelText(/sponsor email/i), { target: { value: 'alex@example.com' } });
    fireEvent.change(screen.getByLabelText(/^department$/i), { target: { value: 'Operations' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    expect(await screen.findByLabelText(/expected benefits/i)).toHaveValue('Reduce manual effort by 20%.');
    fireEvent.change(screen.getByLabelText(/business case summary/i), { target: { value: 'Summary text' } });
    fireEvent.change(screen.getByLabelText(/strategic justification/i), { target: { value: 'Justification text' } });

    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByLabelText(/success metrics/i)).toHaveValue('Improve SLA adherence to 95%.');

    fireEvent.change(input, { target: { value: 'propose overwrite' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(useAssistantStore.getState().actionChips.map((chip) => chip.label)).toContain('Apply expectedBenefits');
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'Apply expectedBenefits' })[0]!);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByRole('button', { name: /back/i }));
    expect(await screen.findByLabelText(/expected benefits/i)).toHaveValue('Reduce manual effort by 20%.');
  });
});
