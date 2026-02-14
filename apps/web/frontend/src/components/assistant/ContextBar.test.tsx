import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { AssistantContext } from '@/store/assistant';
import { ContextBar } from './ContextBar';

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

describe('ContextBar', () => {
  it('starts collapsed and expands on click', () => {
    render(<ContextBar context={context} contextSyncLabel={context.currentActivityName ?? undefined} />);

    const toggle = screen.getByRole('button', { name: /plan > define scope/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText(/Context: Define Scope/i)).toBeInTheDocument();
    expect(screen.queryByText('Project')).not.toBeInTheDocument();

    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Project')).toBeInTheDocument();
    expect(screen.getByText('Apollo')).toBeInTheDocument();
  });
});
