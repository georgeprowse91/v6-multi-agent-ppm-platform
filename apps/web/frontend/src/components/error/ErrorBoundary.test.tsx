import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorBoundary } from '../ui/ErrorBoundary';

const ThrowingChild = () => {
  throw new Error('Boom from child');
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  it('renders recovery actions when a child throws', () => {
    render(
      <ErrorBoundary showActions>
        <ThrowingChild />
      </ErrorBoundary>
    );

    expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to home' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Report issue' })).toBeInTheDocument();
  });

  it('shows extended actions when showActions is enabled', () => {
    render(
      <ErrorBoundary showActions>
        <ThrowingChild />
      </ErrorBoundary>
    );

    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to home' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Report issue' })).toBeInTheDocument();
  });

  it('renders fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingChild />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });
});
