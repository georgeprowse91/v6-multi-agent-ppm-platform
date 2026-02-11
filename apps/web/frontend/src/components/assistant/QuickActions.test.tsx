import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ActionChip } from '@/store/assistant';
import { QuickActions } from './QuickActions';

const makeChip = (
  id: string,
  priority: ActionChip['priority'],
  enabled = true
): ActionChip => ({
  id,
  label: `Chip ${id}`,
  category: 'review',
  priority,
  actionType: 'custom',
  payload: { type: 'custom', actionKey: `handler-${id}` },
  enabled,
});

describe('QuickActions', () => {
  it('returns null when chips are empty', () => {
    const { container } = render(<QuickActions chips={[]} onChipClick={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders only top three chips sorted by priority and shows +N more', () => {
    render(
      <QuickActions
        chips={[
          makeChip('1', 'low'),
          makeChip('2', 'high'),
          makeChip('3', 'medium'),
          makeChip('4', 'high'),
        ]}
        onChipClick={vi.fn()}
      />
    );

    const inlineChipButtons = screen.getAllByRole('button').filter((button) =>
      button.textContent?.includes('Chip')
    );

    expect(inlineChipButtons).toHaveLength(3);
    expect(inlineChipButtons.map((button) => button.textContent)).toEqual([
      'Chip 2',
      'Chip 4',
      'Chip 3',
    ]);
    expect(screen.getByRole('button', { name: /show 1 more quick actions/i })).toBeInTheDocument();
  });

  it('opens popover with all chips and triggers click handler', () => {
    const onChipClick = vi.fn();

    render(
      <QuickActions
        chips={[
          makeChip('1', 'low'),
          makeChip('2', 'high'),
          makeChip('3', 'medium'),
          makeChip('4', 'high'),
        ]}
        onChipClick={onChipClick}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /show 1 more quick actions/i }));

    const chip2Buttons = screen.getAllByRole('button', { name: /chip 2/i });
    expect(chip2Buttons.length).toBeGreaterThan(1);

    fireEvent.click(chip2Buttons[chip2Buttons.length - 1]!);
    expect(onChipClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: '2' })
    );
  });
});
