import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { TourProvider } from './TourProvider';
import { useAppStore } from '@/store';

const startSpy = vi.fn();

vi.mock('shepherd.js', () => ({
  default: {
    Tour: class {
      addStep = vi.fn();
      start = startSpy;
      on = vi.fn();
      next = vi.fn();
      back = vi.fn();
      complete = vi.fn();
    },
  },
}));

describe('TourProvider', () => {
  afterEach(() => {
    startSpy.mockClear();
    localStorage.clear();
  });

  it('shows the onboarding modal for new users', () => {
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: { id: 'user-1', name: 'User', email: 'u@example.com', tenantId: 't1', roles: [] },
      },
    });

    render(
      <MemoryRouter>
        <TourProvider>
          <div>Content</div>
        </TourProvider>
      </MemoryRouter>
    );

    expect(
      screen.getByText('Welcome to the expanded web console')
    ).toBeInTheDocument();
  });

  it('starts the tour from the onboarding modal', () => {
    useAppStore.setState({
      session: {
        authenticated: true,
        loading: false,
        user: { id: 'user-1', name: 'User', email: 'u@example.com', tenantId: 't1', roles: [] },
      },
    });

    render(
      <MemoryRouter>
        <TourProvider>
          <div>Content</div>
        </TourProvider>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Start walkthrough'));
    expect(startSpy).toHaveBeenCalled();
  });
});
