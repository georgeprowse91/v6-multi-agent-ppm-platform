import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePromptStore } from '@/store/prompts';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  beforeEach(() => {
    usePromptStore.setState({ prompts: [], hydrated: false });
  });

  it('supports slash commands for prompt, research, help, and status', async () => {
    const onSubmitMessage = vi.fn().mockResolvedValue(undefined);
    const onStartScopeResearch = vi.fn();

    render(
      <MemoryRouter>
        <ChatInput onSubmitMessage={onSubmitMessage} onStartScopeResearch={onStartScopeResearch} />
      </MemoryRouter>
    );

    const textarea = screen.getByLabelText(/ai assistant chat input/i);

    fireEvent.change(textarea, { target: { value: '/prompt' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(await screen.findByRole('dialog', { name: /prompt picker/i })).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: '/research' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    fireEvent.click(screen.getByRole('button', { name: /start research/i }));
    expect(onStartScopeResearch).toHaveBeenCalledTimes(1);

    fireEvent.change(textarea, { target: { value: '/help' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    fireEvent.change(textarea, { target: { value: '/status' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    await waitFor(() => {
      expect(onSubmitMessage).toHaveBeenCalledWith('help');
      expect(onSubmitMessage).toHaveBeenCalledWith('status');
    });
  });



  it('shows discoverability hints for slash commands when input is empty', () => {
    render(
      <MemoryRouter>
        <ChatInput onSubmitMessage={vi.fn()} onStartScopeResearch={vi.fn()} />
      </MemoryRouter>
    );

    const textarea = screen.getByLabelText(/ai assistant chat input/i);
    expect(textarea).toHaveAttribute('placeholder', 'Type a message or / for commands');

    fireEvent.focus(textarea);
    expect(screen.getByText(/\/prompt/i)).toBeInTheDocument();
    expect(screen.getByText(/\/research/i)).toBeInTheDocument();
  });

  it('auto-grows the textarea up to six rows', async () => {
    const onSubmitMessage = vi.fn();

    render(
      <MemoryRouter>
        <ChatInput onSubmitMessage={onSubmitMessage} onStartScopeResearch={vi.fn()} />
      </MemoryRouter>
    );

    const textarea = screen.getByLabelText(/ai assistant chat input/i);

    Object.defineProperty(textarea, 'scrollHeight', {
      configurable: true,
      get: () => 400,
    });

    fireEvent.change(textarea, { target: { value: 'line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7' } });

    await waitFor(() => {
      expect((textarea as HTMLTextAreaElement).style.height).toBe('168px');
    });
  });
});
