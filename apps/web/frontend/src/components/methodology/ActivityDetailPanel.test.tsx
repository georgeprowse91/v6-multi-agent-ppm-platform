import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ActivityDetailPanel } from './ActivityDetailPanel';

describe('ActivityDetailPanel', () => {
  it('renders runtime actions and executes selected action', () => {
    const onLifecycleAction = vi.fn();
    render(
      <ActivityDetailPanel
        activity={{ id: 'a1', name: 'Activity', status: 'in_progress', canvasType: 'document', prerequisites: [], order: 1 }}
        stageLabel="Stage 1"
        isLocked={false}
        missingPrerequisites={[]}
        runtimeActionsAvailable={['generate', 'review']}
        reviewQueue={[]}
        onLifecycleAction={onLifecycleAction}
        onReviewDecision={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'generate' }));
    expect(onLifecycleAction).toHaveBeenCalledWith('generate');
    expect(screen.getByRole('button', { name: 'review' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'approve' })).not.toBeInTheDocument();
  });
});
