import { useEffect, useState } from 'react';
import { useTranslation } from '@/i18n';
import { useAppStore } from '@/store';
import { canViewAuditLogs } from '@/auth/permissions';
import styles from './AuditLogPage.module.css';

interface AuditEvent {
  event_id: string;
  timestamp: string;
  tenant_id: string;
  actor: { id: string; type: string; roles: string[] };
  action: string;
  resource: { type: string; id: string; metadata?: Record<string, unknown> | null };
  outcome: string;
  metadata?: Record<string, unknown> | null;
}

export function AuditLogPage() {
  const { t } = useTranslation();
  const { session } = useAppStore();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const allowed = canViewAuditLogs(session.user?.roles);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch('/api/v1/audit/events?limit=200');
        if (!response.ok) {
          throw new Error('Failed to fetch audit logs');
        }
        const data = (await response.json()) as AuditEvent[];
        if (mounted) {
          setEvents(data);
        }
      } catch {
        if (mounted) {
          setEvents([]);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [allowed]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{t('audit.title')}</h1>
        <p>{t('audit.description')}</p>
      </header>

      {!allowed && (
        <div className={styles.notice} role="alert">
          {t('audit.accessDenied')}
        </div>
      )}

      {allowed && loading && <div className={styles.loading}>Loading audit events...</div>}

      {allowed && !loading && events.length === 0 && (
        <div className={styles.empty}>{t('audit.empty')}</div>
      )}

      {allowed && !loading && events.length > 0 && (
        <div className={styles.tableWrapper} role="region" aria-label="Audit log table">
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Timestamp</th>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Resource</th>
                <th scope="col">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.event_id}>
                  <td>{new Date(event.timestamp).toLocaleString()}</td>
                  <td>
                    <div className={styles.actor}>
                      <span>{event.actor.id}</span>
                      <span className={styles.actorRoles}>{event.actor.roles.join(', ')}</span>
                    </div>
                  </td>
                  <td>{event.action}</td>
                  <td>
                    <div className={styles.resource}>
                      <span>{event.resource.type}</span>
                      <span className={styles.resourceId}>{event.resource.id}</span>
                    </div>
                  </td>
                  <td>{event.outcome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
