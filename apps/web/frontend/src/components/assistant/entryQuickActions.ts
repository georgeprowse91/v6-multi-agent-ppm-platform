import type { ActionChip } from '@/store/assistant';

export type WorkspaceType = 'portfolio' | 'program' | 'project';

export const ENTRY_ASSISTANT_CHIPS: ActionChip[] = [
  {
    id: 'entry-log-intake',
    label: 'Log new intake',
    category: 'create',
    priority: 'high',
    icon: 'navigation.next',
    actionType: 'custom',
    payload: { type: 'custom', actionKey: 'navigate_intake' },
    enabled: true,
    description: 'Open a fresh intake form.',
  },
  {
    id: 'entry-open-portfolio',
    label: 'Open portfolio workspace',
    category: 'navigate',
    priority: 'medium',
    icon: 'domain.portfolio',
    actionType: 'custom',
    payload: {
      type: 'custom',
      actionKey: 'open_workspace',
      data: { workspaceType: 'portfolio' },
    },
    enabled: true,
    description: 'Open a portfolio workspace by ID.',
  },
  {
    id: 'entry-open-program',
    label: 'Open program workspace',
    category: 'navigate',
    priority: 'medium',
    icon: 'domain.program',
    actionType: 'custom',
    payload: {
      type: 'custom',
      actionKey: 'open_workspace',
      data: { workspaceType: 'program' },
    },
    enabled: true,
    description: 'Open a program workspace by ID.',
  },
  {
    id: 'entry-open-project',
    label: 'Open project workspace',
    category: 'navigate',
    priority: 'medium',
    icon: 'domain.project',
    actionType: 'custom',
    payload: {
      type: 'custom',
      actionKey: 'open_workspace',
      data: { workspaceType: 'project' },
    },
    enabled: true,
    description: 'Open a project workspace by ID.',
  },
];
