export type Role =
  | 'PMO_ADMIN'
  | 'PM'
  | 'TEAM_MEMBER'
  | 'AUDITOR'
  | 'COLLABORATOR'
  | 'tenant_owner'
  | 'portfolio_admin'
  | 'project_manager'
  | 'analyst'
  | 'auditor';

const roleAliases: Record<string, Role> = {
  tenant_owner: 'PMO_ADMIN',
  portfolio_admin: 'PMO_ADMIN',
  project_manager: 'PM',
  analyst: 'TEAM_MEMBER',
  auditor: 'AUDITOR',
  collaborator: 'COLLABORATOR',
};

export function normalizeRoles(roles: string[] | undefined | null): Role[] {
  if (!roles) return [];
  return roles.map((role) => roleAliases[role] ?? (role as Role));
}

export function canManageConfig(roles: string[] | undefined | null): boolean {
  const normalized = normalizeRoles(roles);
  return normalized.includes('PMO_ADMIN') || normalized.includes('PM');
}

export function canViewAuditLogs(roles: string[] | undefined | null): boolean {
  const normalized = normalizeRoles(roles);
  return normalized.includes('PMO_ADMIN') || normalized.includes('AUDITOR');
}

export function canViewConfig(roles: string[] | undefined | null): boolean {
  const normalized = normalizeRoles(roles);
  return normalized.length > 0;
}
