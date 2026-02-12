export type CrashContext = {
  componentStack?: string;
  phase: 'render' | 'bootstrap' | 'session_restore';
  sessionAuthenticated: boolean;
  tenantId: string | null;
};

export const reportCrash = (error: Error, context: CrashContext) => {
  // Placeholder telemetry provider integration point (Sentry, Datadog, etc.)
  console.error('[mobile-telemetry] Unhandled crash', {
    errorName: error.name,
    message: error.message,
    stack: error.stack,
    ...context,
  });
};
