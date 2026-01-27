/**
 * TimelineCanvas - Gantt chart / timeline viewer
 *
 * A placeholder timeline component with mocked bars.
 * Real Gantt functionality will be added in a future iteration.
 */

import { useMemo } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { TimelineContent, TimelineItem } from '../../types/artifact';
import styles from './TimelineCanvas.module.css';

export interface TimelineCanvasProps extends CanvasComponentProps<TimelineContent> {}

/** Calculate days between two dates */
function daysBetween(start: string, end: string): number {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
}

/** Format date for display */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

interface TimelineBarProps {
  item: TimelineItem;
  viewStart: Date;
  totalDays: number;
}

function TimelineBar({ item, viewStart, totalDays }: TimelineBarProps) {
  const itemStart = new Date(item.startDate);
  const itemEnd = new Date(item.endDate);

  const startOffset = Math.max(
    0,
    (itemStart.getTime() - viewStart.getTime()) / (1000 * 60 * 60 * 24)
  );
  const duration = daysBetween(item.startDate, item.endDate);

  const leftPercent = (startOffset / totalDays) * 100;
  const widthPercent = (duration / totalDays) * 100;

  return (
    <div className={styles.row}>
      <div className={styles.rowLabel}>
        <span className={styles.itemName}>{item.name}</span>
        <span className={styles.itemDates}>
          {formatDate(item.startDate)} - {formatDate(item.endDate)}
        </span>
      </div>
      <div className={styles.rowTrack}>
        <div
          className={styles.bar}
          style={{
            left: `${leftPercent}%`,
            width: `${Math.max(widthPercent, 2)}%`,
            backgroundColor: item.color || 'var(--color-primary-500, #6366f1)',
          }}
          title={`${item.name}: ${formatDate(item.startDate)} - ${formatDate(item.endDate)}`}
        >
          {item.progress !== undefined && (
            <div
              className={styles.progress}
              style={{ width: `${item.progress}%` }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export function TimelineCanvas({
  artifact,
  className,
}: TimelineCanvasProps) {
  const { items, viewStart: viewStartStr, viewEnd: viewEndStr } = artifact.content;

  // Calculate view range
  const { viewStart, viewEnd, totalDays, monthHeaders } = useMemo(() => {
    let start: Date;
    let end: Date;

    if (viewStartStr && viewEndStr) {
      start = new Date(viewStartStr);
      end = new Date(viewEndStr);
    } else if (items.length > 0) {
      // Auto-calculate from items
      const dates = items.flatMap(item => [
        new Date(item.startDate),
        new Date(item.endDate),
      ]);
      start = new Date(Math.min(...dates.map(d => d.getTime())));
      end = new Date(Math.max(...dates.map(d => d.getTime())));

      // Add padding
      start.setDate(start.getDate() - 7);
      end.setDate(end.getDate() + 7);
    } else {
      // Default: current month
      start = new Date();
      start.setDate(1);
      end = new Date();
      end.setMonth(end.getMonth() + 2);
    }

    const days = daysBetween(start.toISOString(), end.toISOString());

    // Generate month headers
    const months: { label: string; startPercent: number; widthPercent: number }[] = [];
    const current = new Date(start);
    current.setDate(1);

    while (current <= end) {
      const monthStart = new Date(current);
      const monthEnd = new Date(current.getFullYear(), current.getMonth() + 1, 0);

      const effectiveStart = monthStart < start ? start : monthStart;
      const effectiveEnd = monthEnd > end ? end : monthEnd;

      const startOffset = daysBetween(start.toISOString(), effectiveStart.toISOString());
      const duration = daysBetween(effectiveStart.toISOString(), effectiveEnd.toISOString());

      months.push({
        label: monthStart.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
        startPercent: (startOffset / days) * 100,
        widthPercent: (duration / days) * 100,
      });

      current.setMonth(current.getMonth() + 1);
    }

    return { viewStart: start, viewEnd: end, totalDays: days, monthHeaders: months };
  }, [items, viewStartStr, viewEndStr]);

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <div className={styles.header}>
        <div className={styles.headerLabel}>Tasks</div>
        <div className={styles.headerTimeline}>
          {monthHeaders.map((month, idx) => (
            <div
              key={idx}
              className={styles.monthHeader}
              style={{
                left: `${month.startPercent}%`,
                width: `${month.widthPercent}%`,
              }}
            >
              {month.label}
            </div>
          ))}
        </div>
      </div>

      <div className={styles.body}>
        {items.length === 0 ? (
          <div className={styles.emptyState}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <p>No timeline items yet.</p>
            <p className={styles.hint}>Add tasks with start and end dates to see them here.</p>
          </div>
        ) : (
          items.map(item => (
            <TimelineBar
              key={item.id}
              item={item}
              viewStart={viewStart}
              totalDays={totalDays}
            />
          ))
        )}
      </div>

      <div className={styles.footer}>
        <span className={styles.footerInfo}>
          {items.length} task{items.length !== 1 ? 's' : ''} |{' '}
          {formatDate(viewStart.toISOString())} - {formatDate(viewEnd.toISOString())}
        </span>
      </div>
    </div>
  );
}
