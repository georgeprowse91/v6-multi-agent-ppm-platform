import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import {
  BoardCanvas,
  BacklogCanvas,
  GanttCanvas,
  GridCanvas,
  FinancialCanvas,
  DependencyMapCanvas,
  RoadmapCanvas,
  ApprovalCanvas,
  createArtifact,
  createEmptyContent,
} from '@ppm/canvas-engine';

describe('new canvas types smoke', () => {
  it('board renders and supports editing', () => {
    const onChange = vi.fn();
    render(<BoardCanvas artifact={createArtifact('board', 'Board', 'p1', createEmptyContent('board') as any)} onChange={onChange} />);
    fireEvent.click(screen.getAllByRole('button', { name: /add card/i })[0]);
    expect(onChange).toHaveBeenCalled();
  });

  it('backlog renders and supports editing', () => {
    const onChange = vi.fn();
    render(<BacklogCanvas artifact={createArtifact('backlog', 'Backlog', 'p1', createEmptyContent('backlog') as any)} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /add backlog item/i }));
    expect(onChange).toHaveBeenCalled();
  });

  it('gantt renders and supports editing', () => {
    const onChange = vi.fn();
    render(<GanttCanvas artifact={createArtifact('gantt', 'Gantt', 'p1', createEmptyContent('gantt') as any)} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /add task/i }));
    expect(onChange).toHaveBeenCalled();
  });

  it('grid renders and supports editing', () => {
    const onChange = vi.fn();
    render(<GridCanvas artifact={createArtifact('grid', 'Grid', 'p1', createEmptyContent('grid') as any)} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /add row/i }));
    expect(onChange).toHaveBeenCalled();
  });

  it('financial and dependency/roadmap/approval render', () => {
    render(<FinancialCanvas artifact={createArtifact('financial', 'Financial', 'p1', createEmptyContent('financial') as any)} />);
    render(<DependencyMapCanvas artifact={createArtifact('dependency_map', 'Dependencies', 'p1', createEmptyContent('dependency_map') as any)} />);
    render(<RoadmapCanvas artifact={createArtifact('roadmap', 'Roadmap', 'p1', createEmptyContent('roadmap') as any)} />);
    render(<ApprovalCanvas artifact={createArtifact('approval', 'Approval', 'p1', createEmptyContent('approval') as any)} onChange={vi.fn()} />);
    expect(screen.getByText(/status:/i)).toBeInTheDocument();
  });
});
