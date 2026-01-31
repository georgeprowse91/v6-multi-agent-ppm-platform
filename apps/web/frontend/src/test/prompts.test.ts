import { describe, expect, it } from 'vitest';
import type { PromptDefinition } from '@/types/prompt';
import prompts from '../../../data/prompts.json';

describe('prompt library', () => {
  it('includes required fields on each prompt', () => {
    const promptList = prompts as PromptDefinition[];
    expect(Array.isArray(promptList)).toBe(true);
    promptList.forEach((prompt) => {
      expect(prompt.id).toBeTruthy();
      expect(prompt.label).toBeTruthy();
      expect(prompt.description).toBeTruthy();
      expect(Array.isArray(prompt.tags)).toBe(true);
      expect(prompt.tags.length).toBeGreaterThan(0);
    });
  });
});
