import { useCallback, useMemo, useState } from 'react';

export type RequestStatus = 'idle' | 'loading' | 'success' | 'error';

export function useRequestState() {
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const isLoading = status === 'loading';
  const isError = status === 'error';
  const isSuccess = status === 'success';

  const start = useCallback(() => {
    setStatus('loading');
    setError(null);
  }, []);

  const succeed = useCallback(() => {
    setStatus('success');
    setError(null);
  }, []);

  const fail = useCallback((message: string) => {
    setStatus('error');
    setError(message);
  }, []);

  const reset = useCallback(() => {
    setStatus('idle');
    setError(null);
  }, []);

  return useMemo(
    () => ({ status, error, isLoading, isError, isSuccess, start, succeed, fail, reset }),
    [error, fail, isError, isLoading, isSuccess, reset, start, status, succeed]
  );
}
