/**
 * TimelineCanvas - Gantt chart / timeline viewer
 *
 * A placeholder timeline component with mocked bars.
 * Real Gantt functionality will be added in a future iteration.
 */

import { useMemo, useState, useRef, useCallback, useEffect } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { TimelineContent, TimelineItem, TreeNode } from '../../types/artifact';
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

interface WbsNodeData {
  startDate?: string;
  endDate?: string;
  dependencies?: string[];
  phase?: string;
  resource?: string;
  isMilestone?: boolean;
}

const getWbsData = (node: TreeNode): WbsNodeData => {
  const metadata = node.metadata ?? {};
  const wbs = metadata.wbs;
  if (wbs && typeof wbs === 'object') {
    return wbs as WbsNodeData;
  }
  return {};
};

const toDateString = (date: Date): string => date.toISOString().slice(0, 10);

interface TimelineBarProps {
  item: TimelineItem;
  viewStart: Date;
  totalDays: number;
  onDragStart?: (itemId: string, startX: number) => void;
  readOnly?: boolean;
}

function TimelineBar({ item, viewStart, totalDays, onDragStart, readOnly }: TimelineBarProps) {
  const itemStart = new Date(item.startDate);

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
        <div className={styles.itemTitleRow}>
          <span className={styles.itemName}>{item.name}</span>
          {item.isMilestone && (
            <span
              className={`${styles.gateStatus} ${
                item.gateStatus === 'delayed' ? styles.gateDelayed : styles.gateOnTrack
              }`}
            >
              {item.gateStatus === 'delayed' ? 'Gate delayed' : 'Gate on track'}
            </span>
          )}
        </div>
        <span className={styles.itemDates}>
          {formatDate(item.startDate)} - {formatDate(item.endDate)}
        </span>
        {item.dependencies && item.dependencies.length > 0 && (
          <span className={styles.itemDependencies}>
            Depends on {item.dependencies.length} task{item.dependencies.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      <div className={styles.rowTrack}>
        <div
          className={styles.bar}
          style={{
            left: `${leftPercent}%`,
            width: `${Math.max(widthPercent, 2)}%`,
            backgroundColor: item.color || 'var(--color-dataviz-series-primary)',
          }}
          title={`${item.name}: ${formatDate(item.startDate)} - ${formatDate(item.endDate)}`}
          role={readOnly ? 'img' : 'slider'}
          aria-label={`Timeline bar for ${item.name}`}
          onMouseDown={
            readOnly || !onDragStart
              ? undefined
              : (event) => onDragStart(item.id, event.clientX)
          }
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
  readOnly = false,
  className,
  onChange,
}: TimelineCanvasProps) {
  const { items, viewStart: viewStartStr, viewEnd: viewEndStr, wbs } = artifact.content;
  const [draggingItemId, setDraggingItemId] = useState<string | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartDates, setDragStartDates] = useState<{ start: string; end: string } | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const hasWbs = Boolean(wbs);

  const derivedItems = useMemo(() => {
    if (!wbs) return items;
    const nodes = Object.values(wbs.nodes);
    return nodes
      .filter(node => node.id !== wbs.rootId)
      .map((node): TimelineItem | null => {
        const data = getWbsData(node);
        if (!data.startDate || !data.endDate) {
          return null;
        }
        const isMilestone =
          data.isMilestone || data.startDate === data.endDate;
        return {
          id: node.id,
          name: node.label,
          startDate: data.startDate,
          endDate: data.endDate,
          dependencies: data.dependencies,
          isMilestone,
        };
      })
      .filter((item): item is TimelineItem => Boolean(item));
  }, [items, wbs]);

  const scheduleItems = useMemo(() => {
    const now = new Date();
    return derivedItems.map((item): TimelineItem => {
      if (!item.isMilestone) return item;
      const endDate = new Date(item.endDate);
      const isDelayed = endDate < now;
      const gateStatus: TimelineItem['gateStatus'] = isDelayed ? 'delayed' : 'on-track';
      return {
        ...item,
        gateStatus,
      };
    });
  }, [derivedItems]);

  // Calculate view range
  const { viewStart, viewEnd, totalDays, monthHeaders } = useMemo(() => {
    let start: Date;
    let end: Date;

    if (viewStartStr && viewEndStr) {
      start = new Date(viewStartStr);
      end = new Date(viewEndStr);
    } else if (scheduleItems.length > 0) {
      // Auto-calculate from items
      const dates = scheduleItems.flatMap(item => [
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
  }, [scheduleItems, viewStartStr, viewEndStr]);

  const handleDragStart = useCallback(
    (itemId: string, startX: number) => {
      if (readOnly) return;
      const item = scheduleItems.find(entry => entry.id === itemId);
      if (!item) return;
      setDraggingItemId(itemId);
      setDragStartX(startX);
      setDragStartDates({ start: item.startDate, end: item.endDate });
    },
    [readOnly, scheduleItems]
  );

  useEffect(() => {
    if (!draggingItemId || !dragStartDates) return;
    const handleMouseMove = (event: MouseEvent) => {
      const trackWidth = timelineRef.current?.getBoundingClientRect().width;
      if (!trackWidth) return;
      const deltaX = event.clientX - dragStartX;
      const deltaDays = Math.round((deltaX / trackWidth) * totalDays);
      if (!onChange || deltaDays === 0) return;

      const startDate = new Date(dragStartDates.start);
      const endDate = new Date(dragStartDates.end);
      startDate.setDate(startDate.getDate() + deltaDays);
      endDate.setDate(endDate.getDate() + deltaDays);

      if (hasWbs && wbs) {
        const node = wbs.nodes[draggingItemId];
        if (!node) return;
        const metadata = node.metadata ?? {};
        const wbsData = getWbsData(node);
        const updatedNodes: Record<string, TreeNode> = {
          ...wbs.nodes,
          [draggingItemId]: {
            ...node,
            metadata: {
              ...metadata,
              wbs: {
                ...wbsData,
                startDate: toDateString(startDate),
                endDate: toDateString(endDate),
              },
            },
          },
        };

        onChange({
          ...artifact.content,
          wbs: {
            ...wbs,
            nodes: updatedNodes,
          },
        });
        return;
      }

      const updatedItems = items.map(entry =>
        entry.id === draggingItemId
          ? { ...entry, startDate: toDateString(startDate), endDate: toDateString(endDate) }
          : entry
      );
      onChange({
        ...artifact.content,
        items: updatedItems,
      });
    };

    const handleMouseUp = () => {
      setDraggingItemId(null);
      setDragStartDates(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [
    draggingItemId,
    dragStartDates,
    dragStartX,
    totalDays,
    onChange,
    items,
    artifact.content,
    hasWbs,
    wbs,
  ]);

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

      <div className={styles.body} ref={timelineRef}>
        {scheduleItems.length === 0 ? (
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
          scheduleItems.map(item => (
            <TimelineBar
              key={item.id}
              item={item}
              viewStart={viewStart}
              totalDays={totalDays}
              onDragStart={handleDragStart}
              readOnly={readOnly}
            />
          ))
        )}
      </div>

      <div className={styles.footer}>
        <span className={styles.footerInfo}>
          {scheduleItems.length} task{scheduleItems.length !== 1 ? 's' : ''} |{' '}
          {formatDate(viewStart.toISOString())} - {formatDate(viewEnd.toISOString())}
        </span>
      </div>
    </div>
  );
}
