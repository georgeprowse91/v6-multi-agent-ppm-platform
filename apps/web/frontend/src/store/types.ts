/** Types for PPM Platform state management */

export interface EntitySelection {
  type: 'portfolio' | 'program' | 'project';
  id: string;
  name: string;
}

export interface Activity {
  id: string;
  name: string;
  icon?: string;
}

export interface CanvasTab {
  id: string;
  title: string;
  type: 'document' | 'dashboard' | 'workflow' | 'settings';
  entityId?: string;
  isDirty?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  tenantId: string;
  roles: string[];
  permissions: string[];
}

export interface SessionState {
  authenticated: boolean;
  user: User | null;
  loading: boolean;
}
