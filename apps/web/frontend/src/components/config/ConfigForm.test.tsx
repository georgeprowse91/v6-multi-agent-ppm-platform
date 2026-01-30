import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ConfigForm } from './ConfigForm';

describe('ConfigForm', () => {
  it('validates required fields and submits values', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ConfigForm
        title="Test Form"
        fields={[
          { name: 'name', label: 'Name', type: 'text', required: true },
          { name: 'count', label: 'Count', type: 'number', min: 1 },
        ]}
        initialValues={{ name: '', count: 2 }}
        onSubmit={onSubmit}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('Name is required.')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'Alpha' } });
    fireEvent.change(screen.getByLabelText(/Count/), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Alpha', count: 3 })
      );
    });
  });
});
