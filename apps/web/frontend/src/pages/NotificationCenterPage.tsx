import { useMemo, useState } from 'react';
import { useRealtimeStore } from '@/store/realtime/useRealtimeStore';
import styles from './NotificationCenterPage.module.css';

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  status: 'success' | 'failed' | 'info';
  timestamp: string;
  source?: string;
}

const formatTimestamp = (value: string) => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

export function NotificationCenterPage() {
  const seedNotifications = useMemo<NotificationItem[]>(
    () => [
      {
        id: 'run-2026-09-27-01',
        title: 'Agent run completed',
        message: 'Agent run run-2026-09-27-01 completed successfully.',
        status: 'success',
        timestamp: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
        source: 'Orchestrator',
      },
      {
        id: 'run-2026-09-27-02',
        title: 'Agent run failed',
        message: 'Agent run run-2026-09-27-02 failed during task orchestration.',
        status: 'failed',
        timestamp: new Date(Date.now() - 1000 * 60 * 46).toISOString(),
        source: 'Orchestrator',
      },
      {
        id: 'run-2026-09-27-03',
        title: 'Agent run update',
        message: 'Agent run run-2026-09-27-03 is awaiting downstream inputs.',
        status: 'info',
        timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        source: 'Notification Service',
      },
    ],
    []
  );
  const realtimeNotifications = useRealtimeStore((state) => state.notifications);
  const [notifications] = useState(seedNotifications);
  const combinedNotifications: NotificationItem[] = [
    ...realtimeNotifications.map((item) => ({
      id: item.id,
      title: item.title,
      message: item.message,
      status: (item as { status?: NotificationItem['status'] }).status ?? 'info',
      timestamp: item.timestamp,
      source: item.source,
    })),
    ...notifications,
  ];

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Notification Center</h1>
          <p className={styles.subtitle}>
            Track agent run outcomes and delivery alerts in one place.
          </p>
        </div>
        <button className={styles.actionButton} type="button">
          Mark all as read
        </button>
      </header>

      {combinedNotifications.length === 0 ? (
        <div className={styles.emptyState}>
          <h2>No notifications yet</h2>
          <p>Agent run updates will appear here when notifications are enabled.</p>
        </div>
      ) : (
        <div className={styles.list}>
          {combinedNotifications.map((notification) => (
            <article key={notification.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>{notification.title}</h2>
                  <p className={styles.cardMeta}>
                    {formatTimestamp(notification.timestamp)}
                    {notification.source ? ` • ${notification.source}` : ''}
                  </p>
                </div>
                <span
                  className={`${styles.badge} ${
                    notification.status === 'success'
                      ? styles.badgeSuccess
                      : notification.status === 'failed'
                      ? styles.badgeFailed
                      : styles.badgeInfo
                  }`}
                >
                  {notification.status}
                </span>
              </div>
              <p className={styles.cardMessage}>{notification.message}</p>
              <div className={styles.cardActions}>
                <button className={styles.linkButton} type="button">
                  View details
                </button>
                <button className={styles.linkButton} type="button">
                  Dismiss
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default NotificationCenterPage;
