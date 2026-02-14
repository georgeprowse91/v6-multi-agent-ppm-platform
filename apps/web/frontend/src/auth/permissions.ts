export interface Role {
  id: string;
  name?: string;
  permissions: string[];
  description?: string;
}

export const roleAliases: Record<string, string> = {
  tenant_owner: 'PMO_ADMIN',
  portfolio_admin: 'PMO_ADMIN',
  project_manager: 'PM',
  analyst: 'TEAM_MEMBER',
  auditor: 'AUDITOR',
  collaborator: 'COLLABORATOR',
};

export const permissionOptions = [
  {
    id: 'portfolio.view',
    label: 'View portfolio',
    description: 'Access portfolio, program, and project workspaces.',
  },
  {
    id: 'methodology.edit',
    label: 'Edit methodology',
    description: 'Manage stages, gates, and activity requirements.',
  },
  {
    id: 'intake.approve',
    label: 'Approve intake',
    description: 'Review and approve intake submissions.',
  },
  {
    id: 'config.manage',
    label: 'Manage configuration',
    description: 'Update agents, connectors, and workflows.',
  },
  {
    id: 'analytics.view',
    label: 'View analytics',
    description: 'Access KPI dashboards and analytics summaries.',
  },
  {
    id: 'audit.view',
    label: 'View audit logs',
    description: 'Review audit events and export evidence.',
  },
  {
    id: 'roles.manage',
    label: 'Manage roles',
    description: 'Create roles, assign users, and set permissions.',
  },
];

export function allPermissionIds(): string[] {
  return permissionOptions.map((permission) => permission.id);
}

export function normalizeRoleIds(roles: string[] | undefined | null): string[] {
  if (!roles) return [];
  return roles.map((role) => roleAliases[role] ?? role);
}

export function resolvePermissions(
  roleIds: string[] | undefined | null,
  availableRoles: Role[] | undefined | null
): string[] {
  if (!roleIds || !availableRoles) return [];
  const normalized = normalizeRoleIds(roleIds);
  const permissionSet = new Set<string>();
  const roleMap = new Map(availableRoles.map((role) => [role.id, role]));
  normalized.forEach((roleId) => {
    const role = roleMap.get(roleId);
    role?.permissions?.forEach((permission) => permissionSet.add(permission));
  });
  return Array.from(permissionSet);
}

export function hasPermission(
  permissions: string[] | undefined | null,
  permission: string
): boolean {
  if (!permissions) return false;
  return permissions.includes(permission);
}

export function hasAnyPermission(
  permissions: string[] | undefined | null,
  required: string[]
): boolean {
  if (!permissions) return false;
  return required.some((permission) => permissions.includes(permission));
}

export function canManageConfig(permissions: string[] | undefined | null): boolean {
  return hasPermission(permissions, 'config.manage');
}

export function canViewAuditLogs(permissions: string[] | undefined | null): boolean {
  return hasPermission(permissions, 'audit.view');
}

export function canViewConfig(permissions: string[] | undefined | null): boolean {
  return Boolean(permissions && permissions.length > 0);
}
