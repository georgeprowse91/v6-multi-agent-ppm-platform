import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback UI. If omitted, the default error page is shown. */
  fallback?: ReactNode;
  /** Show full action buttons (reload/home/report). Default: false. */
  showActions?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  private handleReload = (): void => {
    window.location.reload();
  };

  private handleGoHome = (): void => {
    window.location.assign('/');
  };

  private handleReportIssue = (): void => {
    const subject = encodeURIComponent('PPM Platform UI error report');
    const body = encodeURIComponent(
      `I encountered an application error.\n\nError message: ${this.state.error?.message ?? 'Unknown error'}\n\nPlease investigate.`
    );
    window.location.href = `mailto:support@example.com?subject=${subject}&body=${body}`;
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div style={{ maxWidth: '40rem', margin: '5rem auto', padding: '2rem', textAlign: 'center' }}>
        <h2>Something went wrong</h2>
        <p style={{ color: '#666', marginTop: '0.5rem' }}>
          An unexpected error occurred. Please try refreshing the page.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem' }}>
          <button
            onClick={this.handleReset}
            type="button"
            style={{ padding: '0.5rem 1rem', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}
          >
            Try again
          </button>
          {this.props.showActions && (
            <>
              <button onClick={this.handleReload} type="button" style={{ padding: '0.5rem 1rem', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}>
                Reload page
              </button>
              <button onClick={this.handleGoHome} type="button" style={{ padding: '0.5rem 1rem', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}>
                Go to home
              </button>
              <button onClick={this.handleReportIssue} type="button" style={{ padding: '0.5rem 1rem', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}>
                Report issue
              </button>
            </>
          )}
        </div>
      </div>
    );
  }
}
