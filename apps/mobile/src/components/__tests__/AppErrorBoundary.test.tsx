import React from 'react';
import { Text } from 'react-native';
import { fireEvent, render } from '@testing-library/react-native';

import { AppErrorBoundary } from '../AppErrorBoundary';

const Thrower = () => {
  throw new Error('boom');
};

describe('AppErrorBoundary', () => {
  it('shows crash fallback and reports errors', async () => {
    const onReport = jest.fn();

    const screen = render(
      <AppErrorBoundary onRecover={jest.fn()} onSignOut={jest.fn()} onReport={onReport}>
        <Thrower />
      </AppErrorBoundary>
    );

    expect(await screen.findByText('Something went wrong')).toBeTruthy();
    expect(onReport).toHaveBeenCalled();
  });

  it('executes retry and sign out recovery actions', async () => {
    const onRecover = jest.fn();
    const onSignOut = jest.fn();

    const screen = render(
      <AppErrorBoundary onRecover={onRecover} onSignOut={onSignOut} onReport={jest.fn()}>
        <Thrower />
      </AppErrorBoundary>
    );

    await screen.findByText('Something went wrong');

    fireEvent.press(screen.getByText('Try again'));
    expect(onRecover).toHaveBeenCalledTimes(1);

    screen.rerender(
      <AppErrorBoundary onRecover={onRecover} onSignOut={onSignOut} onReport={jest.fn()}>
        <Thrower />
      </AppErrorBoundary>
    );

    await screen.findByText('Something went wrong');
    fireEvent.press(screen.getByText('Sign out'));
    expect(onSignOut).toHaveBeenCalledTimes(1);

    screen.rerender(
      <AppErrorBoundary onRecover={onRecover} onSignOut={onSignOut} onReport={jest.fn()}>
        <Text>Healthy</Text>
      </AppErrorBoundary>
    );
  });
});
