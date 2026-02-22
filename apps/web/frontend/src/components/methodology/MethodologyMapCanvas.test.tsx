/* eslint-disable @typescript-eslint/no-explicit-any */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MethodologyMapCanvas } from './MethodologyMapCanvas';

const stages = [
  {
    id: 'stage-1', name: 'Stage 1', description: '', status: 'not_started', prerequisites: [], order: 1, activities: [
      { id: 'act-1', name: 'Activity 1', status: 'not_started', canvasType: 'document', prerequisites: [], order: 1 },
    ],
  },
] as const;

const monitoring = [
  { id: 'mon-other', name: 'Risk Control', status: 'not_started', canvasType: 'document', prerequisites: [], order: 2, alwaysAccessible: true },
  { id: 'mon-dashboard', name: 'Project Performance & Insights Dashboard', status: 'not_started', canvasType: 'dashboard', prerequisites: [], order: 1, alwaysAccessible: true },
] as const;

describe('MethodologyMapCanvas', () => {
  it('renders stage columns and monitoring band with dashboard first', () => {
    render(
      <MethodologyMapCanvas
        stages={[...stages] as any}
        monitoring={[...monitoring] as any}
        currentActivityId={null}
        isStageLockedComputed={() => false}
        isActivityLockedComputed={() => false}
        templatesRequiredHere={[]}
        templatesInReview={[]}
        onSelectActivity={() => undefined}
      />
    );

    expect(screen.getByText('Stage 1')).toBeInTheDocument();
    expect(screen.getByText(/Monitoring & Controlling/)).toBeInTheDocument();
    const monitoringButtons = screen.getAllByRole('button', { name: /Dashboard|Risk Control/ });
    expect(monitoringButtons[0]).toHaveTextContent('Project Performance & Insights Dashboard');
  });

  it('clicking cards calls selector for stage and monitoring cards', () => {
    const onSelect = vi.fn();
    render(
      <MethodologyMapCanvas
        stages={[...stages] as any}
        monitoring={[...monitoring] as any}
        currentActivityId={null}
        isStageLockedComputed={() => false}
        isActivityLockedComputed={() => false}
        templatesRequiredHere={[]}
        templatesInReview={[]}
        onSelectActivity={onSelect}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Activity 1/ }));
    fireEvent.click(screen.getByRole('button', { name: /Risk Control/ }));

    expect(onSelect).toHaveBeenNthCalledWith(1, expect.objectContaining({ id: 'act-1' }), 'stage-1');
    expect(onSelect).toHaveBeenNthCalledWith(2, expect.objectContaining({ id: 'mon-other' }), 'monitoring');
  });
});
