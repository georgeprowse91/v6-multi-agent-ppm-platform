export interface ApiError {
  name: 'ApiError';
  message: string;
  status: number | null;
  statusText: string | null;
  url?: string;
  method?: string;
  details?: unknown;
  isNetworkError: boolean;
}

const toApiError = (
  message: string,
  response?: Response,
  details?: unknown,
  fallback?: Partial<ApiError>
): ApiError => ({
  name: 'ApiError',
  message,
  status: response?.status ?? fallback?.status ?? null,
  statusText: response?.statusText ?? fallback?.statusText ?? null,
  url: response?.url ?? fallback?.url,
  method: fallback?.method,
  details,
  isNetworkError: fallback?.isNetworkError ?? false,
});

export async function parseJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw toApiError('The server returned an unreadable response.', response);
  }
}

const parseErrorDetails = async (response: Response): Promise<unknown> => {
  try {
    return await response.clone().json();
  } catch {
    try {
      const text = await response.text();
      return text || undefined;
    } catch {
      return undefined;
    }
  }
};

export async function requestJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(input, init);
  } catch {
    throw toApiError('Unable to reach the server. Please check your connection.', undefined, undefined, {
      method: init?.method,
      url: String(input),
      isNetworkError: true,
    });
  }

  if (!response.ok) {
    const details = await parseErrorDetails(response);
    const detailMessage =
      typeof details === 'string'
        ? details
        : typeof details === 'object' && details !== null && 'message' in details
        ? String((details as { message?: unknown }).message)
        : undefined;

    throw toApiError(detailMessage || `Request failed with status ${response.status}.`, response, details, {
      method: init?.method,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return parseJson<T>(response);
}

export const getErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }

  return fallback;
};
