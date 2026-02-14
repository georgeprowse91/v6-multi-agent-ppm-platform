import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { AssistantContext, AssistantMessage } from '@/store/assistant';
import { MessageList } from './MessageList';

const context: AssistantContext = {
  projectId: 'proj-1',
  projectName: 'Apollo',
  methodologyName: 'Stage-Gate',
  currentStageId: 'stage-1',
  currentStageName: 'Plan',
  stageProgress: 42,
  currentActivityId: 'act-1',
  currentActivityName: 'Define Scope',
  currentActivityStatus: 'in_progress',
  currentActivityCanvasType: 'document',
  isCurrentActivityLocked: false,
  incompletePrerequisites: [],
};

describe('MessageList', () => {
  it('renders welcome card when empty', () => {
    render(<MessageList messages={[]} aiState="idle" context={context} onChipClick={vi.fn()} />);

    expect(screen.getByText(/welcome to your project assistant/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /open define scope/i })).toBeInTheDocument();
  });

  it('renders typing indicator for thinking/streaming/tool_use states', () => {
    const { rerender } = render(<MessageList messages={[]} aiState="thinking" context={context} onChipClick={vi.fn()} />);
    expect(screen.getByText('Planning response…')).toBeInTheDocument();

    rerender(<MessageList messages={[]} aiState="streaming" context={context} onChipClick={vi.fn()} />);
    expect(screen.getByText('Drafting response…')).toBeInTheDocument();

    rerender(
      <MessageList
        messages={[]}
        aiState="tool_use"
        typingStatus={{ detail: 'Step 2 of 3: Aggregating results…', step: 2, totalSteps: 3 }}
        context={context}
        onChipClick={vi.fn()}
      />
    );
    expect(screen.getByText('Step 2 of 3: Aggregating results…')).toBeInTheDocument();
  });

  it('renders scope research and conversational command as inline cards', () => {
    const messages: AssistantMessage[] = [
      {
        id: 'scope-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        messageType: 'scope_research',
        data: {
          scope: [{ id: 's-1', text: 'Define MVP scope', status: 'pending' }],
          requirements: [],
          wbs: [],
          sources: ['https://example.com'],
        },
      },
      {
        id: 'cmd-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        messageType: 'conversational_command',
        data: {
          title: 'Apply updates',
          changes: [{ id: 'c1', label: 'Budget', before: '$10k', after: '$12k' }],
        },
      },
    ];

    render(<MessageList messages={messages} aiState="idle" context={context} onChipClick={vi.fn()} />);

    expect(screen.getByText(/scope research results/i)).toBeInTheDocument();
    expect(screen.getAllByText(/apply updates/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
