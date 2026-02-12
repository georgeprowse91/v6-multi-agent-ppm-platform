import React from 'react';

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error?: Error;
};

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ui_error_boundary', { error, info });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.assign('/');
  };

  handleReportIssue = () => {
    const subject = encodeURIComponent('PPM Platform UI error report');
    const body = encodeURIComponent(
      `I encountered an application error.\n\nError message: ${this.state.error?.message ?? 'Unknown error'}\n\nPlease investigate.`
    );
    window.location.href = `mailto:support@example.com?subject=${subject}&body=${body}`;
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ maxWidth: '40rem', margin: '5rem auto', padding: '2rem', textAlign: 'center' }}>
          <h1>We hit an unexpected issue</h1>
          <p>
            You can quickly recover by reloading, returning to the home page, or sending a report to
            support.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button onClick={this.handleReload} type="button">
              Reload page
            </button>
            <button onClick={this.handleGoHome} type="button">
              Go to home
            </button>
            <button onClick={this.handleReportIssue} type="button">
              Report issue
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
