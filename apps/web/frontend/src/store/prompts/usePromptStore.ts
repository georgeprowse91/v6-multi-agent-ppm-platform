import { create } from 'zustand';
import type { PromptDefinition } from '@/types/prompt';
import defaultPrompts from './defaultPrompts';

const STORAGE_KEY = 'ppm_prompt_library';

const getStorage = (): Storage | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.localStorage;
  } catch (error) {
    console.warn('Prompt storage unavailable.', error);
    return null;
  }
};

const loadStoredPrompts = (): PromptDefinition[] => {
  const storage = getStorage();
  if (!storage) {
    return defaultPrompts;
  }
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultPrompts;
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return defaultPrompts;
    }
    return parsed as PromptDefinition[];
  } catch (error) {
    console.warn('Failed to load prompts from storage.', error);
    return defaultPrompts;
  }
};

const persistPrompts = (prompts: PromptDefinition[]) => {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(prompts));
  } catch (error) {
    console.warn('Failed to save prompts to storage.', error);
  }
};

interface PromptStoreState {
  prompts: PromptDefinition[];
  hydrated: boolean;
  hydratePrompts: () => void;
  addPrompt: (prompt: PromptDefinition) => void;
  updatePrompt: (promptId: string, updates: Partial<PromptDefinition>) => void;
  deletePrompt: (promptId: string) => void;
}

export const usePromptStore = create<PromptStoreState>((set, get) => ({
  prompts: defaultPrompts,
  hydrated: false,
  hydratePrompts: () => {
    const stored = loadStoredPrompts();
    set({ prompts: stored, hydrated: true });
  },
  addPrompt: (prompt) => {
    const nextPrompts = [...get().prompts, prompt];
    persistPrompts(nextPrompts);
    set({ prompts: nextPrompts });
  },
  updatePrompt: (promptId, updates) => {
    const nextPrompts = get().prompts.map((prompt) =>
      prompt.id === promptId ? { ...prompt, ...updates } : prompt
    );
    persistPrompts(nextPrompts);
    set({ prompts: nextPrompts });
  },
  deletePrompt: (promptId) => {
    const nextPrompts = get().prompts.filter((prompt) => prompt.id !== promptId);
    persistPrompts(nextPrompts);
    set({ prompts: nextPrompts });
  },
}));

export default usePromptStore;
