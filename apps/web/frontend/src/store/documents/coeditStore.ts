import { create } from 'zustand';

export interface CoeditCursor {
  position: number;
  selectionLength?: number;
  blockId?: string;
}

export interface CoeditParticipant {
  userId: string;
  userName: string;
  joinedAt: string;
}

export interface CoeditConflict {
  conflictId: string;
  baseVersion: number;
  currentVersion: number;
  receivedAt: string;
}

interface CoeditState {
  sessionId: string | null;
  documentId: string | null;
  connected: boolean;
  content: string;
  version: number;
  participants: CoeditParticipant[];
  cursors: Record<string, CoeditCursor>;
  conflicts: CoeditConflict[];
  error: string | null;
  connect: (options: {
    sessionId: string;
    documentId: string;
    userId: string;
    userName?: string;
  }) => void;
  disconnect: () => void;
  sendContentUpdate: (content: string) => void;
  updateCursor: (cursor: CoeditCursor) => void;
  clearConflicts: () => void;
}

let socket: WebSocket | null = null;

const resolveBaseUrl = (): string => {
  const envUrl = import.meta.env?.VITE_COEDIT_WS_URL as string | undefined;
  return envUrl ?? 'ws://localhost:8080';
};

const toWebSocketUrl = (baseUrl: string, path: string): string => {
  let url = baseUrl;
  if (baseUrl.startsWith('http://')) {
    url = baseUrl.replace('http://', 'ws://');
  } else if (baseUrl.startsWith('https://')) {
    url = baseUrl.replace('https://', 'wss://');
  }
  return `${url.replace(/\/$/, '')}${path}`;
};

export const useCoeditStore = create<CoeditState>((set, get) => ({
  sessionId: null,
  documentId: null,
  connected: false,
  content: '',
  version: 0,
  participants: [],
  cursors: {},
  conflicts: [],
  error: null,
  connect: ({ sessionId, documentId, userId, userName }) => {
    if (socket) {
      socket.close();
    }

    const baseUrl = resolveBaseUrl();
    const params = new URLSearchParams({
      session_id: sessionId,
      user_id: userId,
      user_name: userName ?? 'Anonymous',
    });
    const url = toWebSocketUrl(baseUrl, `/ws/documents/${documentId}?${params}`);
    socket = new WebSocket(url);

    set({ sessionId, documentId, error: null });

    socket.onopen = () => {
      set({ connected: true, error: null });
    };

    socket.onclose = () => {
      set({ connected: false });
    };

    socket.onerror = () => {
      set({ error: 'Unable to connect to co-edit service.' });
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string);
        switch (message.type) {
          case 'session_state':
            set({
              content: message.content ?? '',
              version: message.version ?? 0,
              participants: message.participants ?? [],
              cursors: message.cursors ?? {},
            });
            break;
          case 'presence_update':
            set({ participants: message.participants ?? [] });
            break;
          case 'cursor_update':
            set((state) => ({
              cursors: {
                ...state.cursors,
                [message.user_id]: message.cursor ?? { position: 0 },
              },
            }));
            break;
          case 'content_update':
            set((state) => ({
              content: message.content ?? state.content,
              version: message.version ?? state.version,
              conflicts: message.conflict
                ? [
                    ...state.conflicts,
                    {
                      conflictId: message.conflict.conflict_id,
                      baseVersion: message.conflict.base_version,
                      currentVersion: message.conflict.current_version,
                      receivedAt: message.conflict.received_at,
                    },
                  ]
                : state.conflicts,
            }));
            break;
          case 'error':
            set({ error: message.message ?? 'Co-edit error.' });
            break;
          default:
            break;
        }
      } catch (err) {
        set({ error: 'Failed to parse co-edit update.' });
      }
    };
  },
  disconnect: () => {
    if (socket) {
      socket.close();
      socket = null;
    }
    set({ connected: false, sessionId: null, documentId: null });
  },
  sendContentUpdate: (content) => {
    const { version } = get();
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      set({ error: 'Co-edit connection not ready.' });
      return;
    }
    socket.send(
      JSON.stringify({
        type: 'content_update',
        content,
        base_version: version,
      })
    );
  },
  updateCursor: (cursor) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    socket.send(
      JSON.stringify({
        type: 'cursor_update',
        cursor,
      })
    );
  },
  clearConflicts: () => set({ conflicts: [] }),
}));
