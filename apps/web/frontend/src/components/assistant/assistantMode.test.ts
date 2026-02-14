import { describe, expect, it } from 'vitest';
import { resolveAssistantMode } from './assistantMode';

describe('resolveAssistantMode', () => {
  it('returns entry mode for non-context routes', () => {
    expect(resolveAssistantMode('/')).toBe('entry');
    expect(resolveAssistantMode('/search')).toBe('entry');
  });

  it('returns intake mode for intake routes', () => {
    expect(resolveAssistantMode('/intake/new')).toBe('intake');
    expect(resolveAssistantMode('/intake/status/123')).toBe('intake');
  });

  it('returns workspace mode for workspace routes', () => {
    expect(resolveAssistantMode('/portfolio/demo')).toBe('workspace');
    expect(resolveAssistantMode('/projects/demo')).toBe('workspace');
    expect(resolveAssistantMode('/programs/demo')).toBe('workspace');
  });
});
