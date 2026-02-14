import { create } from 'zustand';

export interface IntakeAssistantContext {
  stepId: string;
  stepIndex: number;
  formState: Record<string, string>;
  errors: Record<string, string>;
}

interface IntakePatchRequest {
  id: string;
  field: string;
  value: string;
}

interface IntakeAssistantState {
  context: IntakeAssistantContext | null;
  pendingPatches: IntakePatchRequest[];
  setContext: (context: IntakeAssistantContext) => void;
  clearContext: () => void;
  enqueuePatch: (field: string, value: string) => void;
  consumePatch: (id: string) => void;
}

export const useIntakeAssistantStore = create<IntakeAssistantState>((set) => ({
  context: null,
  pendingPatches: [],
  setContext: (context) => set({ context }),
  clearContext: () => set({ context: null, pendingPatches: [] }),
  enqueuePatch: (field, value) =>
    set((state) => ({
      pendingPatches: [...state.pendingPatches, { id: crypto.randomUUID(), field, value }],
    })),
  consumePatch: (id) =>
    set((state) => ({
      pendingPatches: state.pendingPatches.filter((patch) => patch.id !== id),
    })),
}));
