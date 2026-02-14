import { Fragment, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
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

const REDACTED_TEXT = '[REDACTED]';
const sensitiveKeyMatchers = [
  /token/i,
  /secret/i,
  /password/i,
  /authorization/i,
  /api[_-]?key/i,
  /session/i,
  /cookie/i,
];

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const shouldRedactKey = (key: string) => sensitiveKeyMatchers.some((matcher) => matcher.test(key));

const redactValue = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map((item) => redactValue(item));
  }
  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [
        key,
        shouldRedactKey(key) ? REDACTED_TEXT : redactValue(nestedValue),
      ]),
    );
  }
  return value;
};

const redactMetadata = (metadata?: Record<string, unknown> | null) => {
  if (!metadata) return null;
  return redactValue(metadata) as Record<string, unknown>;
};

const getMetadataValue = (
  metadata: Record<string, unknown> | null,
  keys: string[],
): unknown => {
  if (!metadata) return undefined;
  for (const key of keys) {
    if (key in metadata) {
      return metadata[key];
    }
  }
  return undefined;
};

const formatMetadataValue = (value: unknown) => {
  if (value === undefined) return null;
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
};

export function AuditLogPage() {
  const { t } = useTranslation();
  const { session } = useAppStore();
  const [searchParams] = useSearchParams();
  const eventId = searchParams.get('eventId');
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [focusedEvent, setFocusedEvent] = useState<AuditEvent | null>(null);
  const [focusedLoading, setFocusedLoading] = useState(false);
  const [exportingEvidence, setExportingEvidence] = useState(false);

  const allowed = canViewAuditLogs(session.user?.permissions);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch('/v1/audit/events?limit=200');
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

  useEffect(() => {
    if (!allowed || !eventId) {
      setFocusedEvent(null);
      return;
    }
    let mounted = true;
    const loadFocused = async () => {
      try {
        setFocusedLoading(true);
        const response = await fetch(`/v1/audit/events/${encodeURIComponent(eventId)}`);
        if (!response.ok) {
          throw new Error('Failed to fetch audit event');
        }
        const data = (await response.json()) as AuditEvent;
        if (mounted) {
          setFocusedEvent(data);
        }
      } catch {
        if (mounted) setFocusedEvent(null);
      } finally {
        if (mounted) setFocusedLoading(false);
      }
    };
    loadFocused();
    return () => {
      mounted = false;
    };
  }, [allowed, eventId]);

  const handleExportEvidence = async () => {
    setExportingEvidence(true);
    try {
      const response = await fetch('/v1/api/audit/evidence/export');
      if (!response.ok) {
        throw new Error('Failed to export audit evidence');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'audit-evidence.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setExportingEvidence(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{t('audit.title')}</h1>
        <p>{t('audit.description')}</p>
        {allowed && (
          <button type="button" onClick={() => void handleExportEvidence()} disabled={exportingEvidence}>
            {exportingEvidence ? 'Exporting evidence…' : 'Export evidence pack'}
          </button>
        )}
      </header>

      {!allowed && (
        <div className={styles.notice} role="alert">
          {t('audit.accessDenied')}
        </div>
      )}

      {allowed && loading && (
        <div className={styles.loading} role="status" aria-live="polite">
          {t('audit.loading')}
        </div>
      )}

      {allowed && eventId && (
        <div className={styles.notice} role="region" aria-live="polite">
          {focusedLoading && <p>{t('audit.loading')}</p>}
          {!focusedLoading && focusedEvent && (
            <div>
              <strong>Focused audit event:</strong> {focusedEvent.event_id}
            </div>
          )}
          {!focusedLoading && !focusedEvent && (
            <div>Audit event {eventId} could not be found.</div>
          )}
        </div>
      )}

      {allowed && !loading && events.length === 0 && (
        <div className={styles.empty}>{t('audit.empty')}</div>
      )}

      {allowed && !loading && events.length > 0 && (
        <div className={styles.tableWrapper} role="region" aria-label={t('audit.tableLabel')}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{t('audit.column.timestamp')}</th>
                <th scope="col">{t('audit.column.actor')}</th>
                <th scope="col">{t('audit.column.action')}</th>
                <th scope="col">{t('audit.column.resource')}</th>
                <th scope="col">{t('audit.column.outcome')}</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => {
                const isAgentEvent = event.actor.type === 'agent';
                const redactedResourceMetadata = redactMetadata(event.resource.metadata);
                const redactedMetadata = redactMetadata(event.metadata);
                const correlationId = formatMetadataValue(
                  getMetadataValue(redactedMetadata, ['correlation_id', 'correlationId']),
                );
                const policyReason = formatMetadataValue(
                  getMetadataValue(redactedMetadata, [
                    'policy_reason',
                    'policyReason',
                    'policy_reasons',
                    'policyReasons',
                  ]),
                );

                return (
                  <Fragment key={event.event_id}>
                    <tr>
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
                    {isAgentEvent && (
                      <tr className={styles.detailsRow}>
                        <td colSpan={5}>
                          <details className={styles.details}>
                            <summary>{t('audit.details.summary')}</summary>
                            <div className={styles.detailsGrid}>
                              <div className={styles.detailsSection}>
                                <h4>{t('audit.details.highlights')}</h4>
                                <dl className={styles.detailsList}>
                                  <div>
                                    <dt>{t('audit.details.correlationId')}</dt>
                                    <dd>{correlationId ?? t('audit.details.emptyMetadata')}</dd>
                                  </div>
                                  <div>
                                    <dt>{t('audit.details.policyReason')}</dt>
                                    <dd>{policyReason ?? t('audit.details.emptyMetadata')}</dd>
                                  </div>
                                </dl>
                              </div>
                              <div className={styles.detailsSection}>
                                <h4>{t('audit.details.resourceMetadata')}</h4>
                                {redactedResourceMetadata ? (
                                  <pre className={styles.detailsCode}>
                                    {JSON.stringify(redactedResourceMetadata, null, 2)}
                                  </pre>
                                ) : (
                                  <p className={styles.detailsEmpty}>
                                    {t('audit.details.emptyMetadata')}
                                  </p>
                                )}
                              </div>
                              <div className={styles.detailsSection}>
                                <h4>{t('audit.details.eventMetadata')}</h4>
                                {redactedMetadata ? (
                                  <pre className={styles.detailsCode}>
                                    {JSON.stringify(redactedMetadata, null, 2)}
                                  </pre>
                                ) : (
                                  <p className={styles.detailsEmpty}>
                                    {t('audit.details.emptyMetadata')}
                                  </p>
                                )}
                              </div>
                            </div>
                          </details>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AuditLogPage;
