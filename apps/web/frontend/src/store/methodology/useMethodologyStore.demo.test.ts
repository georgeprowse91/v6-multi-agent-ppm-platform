import { afterEach, describe, expect, it, vi } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { useMethodologyStore } from './useMethodologyStore';

const workspacePayload = {
  project_id: 'demo-predictive',
  methodology: 'predictive',
  current_activity_id: '0.1.1-intake-review',
  available_methodologies: ['predictive', 'adaptive', 'hybrid'],
  methodology_map_summary: {
    id: 'predictive',
    name: 'Predictive',
    description: 'YAML-backed methodology',
    stages: [
      {
        id: '0.1-demand-intake-triage',
        name: 'Demand Intake & Triage',
        activities: [
          {
            id: '0.1.1-intake-review',
            name: 'Intake Review',
            description: 'Review intake',
            prerequisites: [],
            category: 'intake',
            recommended_canvas_tab: 'document',
            assistant_prompts: [],
            access: { allowed: true },
            completed: true,
          },
        ],
      },
    ],
    monitoring: [
      {
        id: 'monitoring-project-performance-insights',
        name: 'Project Performance & Insights Dashboard',
        description: 'Monitoring card',
        prerequisites: [],
        category: 'monitoring',
        recommended_canvas_tab: 'dashboard',
        assistant_prompts: [],
        access: { allowed: true },
        completed: false,
      },
    ],
  },
};

describe('methodology store hydration in demo mode', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('hydrates from backend workspace endpoint and does not rely on demoData stubs', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(workspacePayload), { status: 200 })
    );

    await useMethodologyStore.getState().hydrateFromWorkspace('demo-predictive');

    expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('/api/workspace/demo-predictive'), undefined);
    expect(useMethodologyStore.getState().projectMethodology.methodology.id).toBe('predictive');
    expect(useMethodologyStore.getState().projectMethodology.methodology.stages[0]?.id).toBe('0.1-demand-intake-triage');
  });


  it('uses workspace APIs from SPA routes without depending on /workspace HTML entrypoints', async () => {
    window.history.pushState({}, '', '/app/projects/demo-predictive');
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(workspacePayload), { status: 200 })
    );

    await useMethodologyStore.getState().hydrateFromWorkspace('demo-predictive', 'adaptive');

    expect(fetchSpy).toHaveBeenCalledWith('/api/workspace/demo-predictive?methodology=adaptive', undefined);
  });

  it('does not import demoData.ts in methodology store', () => {
    const sourcePath = path.join(path.dirname(fileURLToPath(import.meta.url)), 'useMethodologyStore.ts');
    const source = fs.readFileSync(sourcePath, 'utf-8');
    expect(source).not.toContain("./demoData");
  });
});
