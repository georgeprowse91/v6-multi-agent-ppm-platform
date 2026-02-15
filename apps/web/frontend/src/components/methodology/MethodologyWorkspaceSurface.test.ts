import { describe, it, expect } from 'vitest';
import { resolveRuntimeCanvasType } from './MethodologyWorkspaceSurface';

describe('MethodologyWorkspaceSurface runtime canvas mapping', () => {
  it('maps runtime aliases to new first-class canvas types', () => {
    expect(resolveRuntimeCanvasType('kanban', 'document')).toBe('board');
    expect(resolveRuntimeCanvasType('risk_log', 'document')).toBe('grid');
    expect(resolveRuntimeCanvasType('decision_log', 'document')).toBe('approval');
    expect(resolveRuntimeCanvasType('form', 'document')).toBe('grid');
  });

  it('passes through new runtime type values', () => {
    expect(resolveRuntimeCanvasType('financial', 'document')).toBe('financial');
    expect(resolveRuntimeCanvasType('dependency_map', 'document')).toBe('dependency_map');
  });
});
