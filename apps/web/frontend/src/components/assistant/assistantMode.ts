import type { AssistantMode } from '@/store/assistant';

const WORKSPACE_ROUTE_PATTERN = /^\/(?:portfolio|portfolios|program|programs|project|projects)\//;

export function resolveAssistantMode(pathname: string): AssistantMode {
  if (pathname.startsWith('/intake/')) {
    return 'intake';
  }

  if (WORKSPACE_ROUTE_PATTERN.test(pathname)) {
    return 'workspace';
  }

  return 'entry';
}
