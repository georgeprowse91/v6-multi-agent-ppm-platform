import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { hasPermission, permissionOptions, type Role } from '@/auth/permissions';
import { useAppStore } from '@/store';
import styles from './RoleManager.module.css';

const API_BASE = '/v1';

interface RoleAssignment {
  user_id: string;
  role_ids: string[];
}

const emptyRole: Role = {
  id: '',
  name: '',
  permissions: [],
  description: '',
};

export type RoleManagerView = 'roles' | 'assignments' | 'all';

interface RoleManagerProps {
  view?: RoleManagerView;
}

export function RoleManager({ view = 'all' }: RoleManagerProps) {
  const { session } = useAppStore();
  const canManage = hasPermission(session.user?.permissions, 'roles.manage');
  const [roles, setRoles] = useState<Role[]>([]);
  const [assignments, setAssignments] = useState<RoleAssignment[]>([]);
  const [newRole, setNewRole] = useState<Role>({ ...emptyRole });
  const [assignmentUser, setAssignmentUser] = useState('');
  const [assignmentRoles, setAssignmentRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const roleOptions = useMemo(() => roles.map((role) => role.id), [roles]);

  const loadRoles = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/roles`);
    if (!response.ok) {
      throw new Error('Unable to load roles.');
    }
    const data = (await response.json()) as Role[];
    setRoles(data);
  }, []);

  const loadAssignments = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/roles/assignments`);
    if (!response.ok) {
      throw new Error('Unable to load role assignments.');
    }
    const data = (await response.json()) as RoleAssignment[];
    setAssignments(data);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await loadRoles();
      if (canManage) {
        await loadAssignments();
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load role data.');
    } finally {
      setLoading(false);
    }
  }, [canManage, loadAssignments, loadRoles]);

  useEffect(() => {
    if (canManage) {
      void refresh();
    } else {
      setLoading(false);
    }
  }, [canManage, refresh]);

  const togglePermission = (role: Role, permissionId: string) => {
    const permissions = role.permissions.includes(permissionId)
      ? role.permissions.filter((permission) => permission !== permissionId)
      : [...role.permissions, permissionId];
    return { ...role, permissions };
  };

  const handleCreateRole = async () => {
    if (!newRole.id || !newRole.name) {
      setError('Role ID and name are required.');
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newRole),
      });
      if (!response.ok) {
        throw new Error('Unable to create role.');
      }
      setSuccess('Role saved.');
      setNewRole({ ...emptyRole });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create role.');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateRole = async (role: Role) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/roles/${encodeURIComponent(role.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(role),
      });
      if (!response.ok) {
        throw new Error('Unable to update role.');
      }
      setSuccess(`Role ${role.name} updated.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update role.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/roles/${encodeURIComponent(roleId)}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Unable to delete role.');
      }
      setSuccess('Role removed.');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete role.');
    } finally {
      setSaving(false);
    }
  };

  const handleAssignmentSave = async () => {
    if (!assignmentUser) {
      setError('User ID is required for assignments.');
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/roles/assignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: assignmentUser, role_ids: assignmentRoles }),
      });
      if (!response.ok) {
        throw new Error('Unable to save role assignment.');
      }
      setSuccess('Assignment saved.');
      setAssignmentUser('');
      setAssignmentRoles([]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save role assignment.');
    } finally {
      setSaving(false);
    }
  };

  const roleLookup = useMemo(
    () => new Map(roles.map((role) => [role.id, role.name || role.id])),
    [roles]
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Role management</h1>
        <p className={styles.muted}>
          Create roles, assign permissions, and link users to role profiles.
        </p>
      </header>

      {!canManage && (
        <div className={styles.notice}>
          You do not have permission to manage roles. Contact a PMO admin to request access.
        </div>
      )}

      {error && <div className={styles.notice}>{error}</div>}
      {success && <div className={styles.notice}>{success}</div>}

      {canManage && (
        <>
          <nav className={styles.actions} aria-label="Role admin navigation">
            <Link to="/app/admin/roles" className={styles.buttonPrimary}>Role catalog</Link>
            <Link to="/app/admin/roles/assignments" className={styles.buttonPrimary}>Role assignments</Link>
          </nav>

          {(view === 'all' || view === 'roles') && <section className={styles.section}>
            <h2>Create role</h2>
            <div className={styles.card}>
              <label className={styles.field}>
                Role ID
                <input
                  value={newRole.id}
                  onChange={(event) =>
                    setNewRole((current) => ({ ...current, id: event.target.value }))
                  }
                  placeholder="e.g. PORTFOLIO_VIEWER"
                />
              </label>
              <label className={styles.field}>
                Role name
                <input
                  value={newRole.name}
                  onChange={(event) =>
                    setNewRole((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Portfolio Viewer"
                />
              </label>
              <label className={styles.field}>
                Description
                <textarea
                  rows={2}
                  value={newRole.description ?? ''}
                  onChange={(event) =>
                    setNewRole((current) => ({ ...current, description: event.target.value }))
                  }
                  placeholder="Optional summary for this role."
                />
              </label>
              <div className={styles.checkboxGroup}>
                {permissionOptions.map((permission) => (
                  <label key={permission.id} className={styles.checkbox}>
                    <input
                      type="checkbox"
                      checked={newRole.permissions.includes(permission.id)}
                      onChange={() =>
                        setNewRole((current) => togglePermission(current, permission.id))
                      }
                    />
                    <span>
                      {permission.label}
                      <div className={styles.muted}>{permission.description}</div>
                    </span>
                  </label>
                ))}
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.buttonPrimary}
                  onClick={handleCreateRole}
                  disabled={saving}
                >
                  Save role
                </button>
              </div>
            </div>
          </section>}

          {(view === 'all' || view === 'roles') && <section className={styles.section}>
            <h2>Existing roles</h2>
            {loading && <div className={styles.emptyState}>Loading roles…</div>}
            {!loading && roles.length === 0 && (
              <div className={styles.emptyState}>No roles configured yet.</div>
            )}
            <div className={styles.grid}>
              {roles.map((role) => (
                <div key={role.id} className={styles.card}>
                  <div className={styles.cardTitle}>
                    <label className={styles.field}>
                      Role ID
                      <input
                        value={role.id}
                        disabled
                      />
                    </label>
                    <label className={styles.field}>
                      Role name
                      <input
                        value={role.name ?? ''}
                        onChange={(event) =>
                          setRoles((current) =>
                            current.map((entry) =>
                              entry.id === role.id ? { ...entry, name: event.target.value } : entry
                            )
                          )
                        }
                      />
                    </label>
                    <label className={styles.field}>
                      Description
                      <textarea
                        rows={2}
                        value={role.description ?? ''}
                        onChange={(event) =>
                          setRoles((current) =>
                            current.map((entry) =>
                              entry.id === role.id
                                ? { ...entry, description: event.target.value }
                                : entry
                            )
                          )
                        }
                      />
                    </label>
                  </div>
                  <div className={styles.checkboxGroup}>
                    {permissionOptions.map((permission) => (
                      <label key={`${role.id}-${permission.id}`} className={styles.checkbox}>
                        <input
                          type="checkbox"
                          checked={role.permissions.includes(permission.id)}
                          onChange={() =>
                            setRoles((current) =>
                              current.map((entry) =>
                                entry.id === role.id
                                  ? togglePermission(entry, permission.id)
                                  : entry
                              )
                            )
                          }
                        />
                        <span>
                          {permission.label}
                          <div className={styles.muted}>{permission.description}</div>
                        </span>
                      </label>
                    ))}
                  </div>
                  <div className={styles.actions}>
                    <button
                      type="button"
                      className={styles.buttonPrimary}
                      onClick={() => handleUpdateRole(role)}
                      disabled={saving}
                    >
                      Update role
                    </button>
                    <button
                      type="button"
                      className={styles.buttonDanger}
                      onClick={() => handleDeleteRole(role.id)}
                      disabled={saving}
                    >
                      Delete role
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>}

          {(view === 'all' || view === 'assignments') && <section className={styles.section}>
            <h2>Assign users</h2>
            <div className={styles.card}>
              <label className={styles.field}>
                User ID
                <input
                  value={assignmentUser}
                  onChange={(event) => setAssignmentUser(event.target.value)}
                  placeholder="user@example.com"
                />
              </label>
              <div className={styles.checkboxGroup}>
                {roleOptions.map((roleId) => (
                  <label key={`assign-${roleId}`} className={styles.checkbox}>
                    <input
                      type="checkbox"
                      checked={assignmentRoles.includes(roleId)}
                      onChange={() =>
                        setAssignmentRoles((current) =>
                          current.includes(roleId)
                            ? current.filter((entry) => entry !== roleId)
                            : [...current, roleId]
                        )
                      }
                    />
                    <span>{roleLookup.get(roleId) ?? roleId}</span>
                  </label>
                ))}
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.buttonPrimary}
                  onClick={handleAssignmentSave}
                  disabled={saving}
                >
                  Save assignment
                </button>
              </div>
            </div>

            <div className={styles.assignmentList}>
              {assignments.length === 0 && (
                <div className={styles.emptyState}>No user assignments yet.</div>
              )}
              {assignments.map((assignment) => (
                <div key={assignment.user_id} className={styles.assignmentRow}>
                  <span>{assignment.user_id}</span>
                  <span>
                    {assignment.role_ids.map((roleId) => roleLookup.get(roleId) ?? roleId).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          </section>}
        </>
      )}
    </div>
  );
}

export default RoleManager;
