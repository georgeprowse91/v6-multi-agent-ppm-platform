/**
 * DashboardCanvas - Widget-based dashboard
 *
 * A placeholder dashboard with mock widgets.
 * Real charts and data binding will be added in a future iteration.
 */

import type { CanvasComponentProps } from '../../types/canvas';
import type { DashboardContent, DashboardWidget } from '../../types/artifact';
import styles from './DashboardCanvas.module.css';

export interface DashboardCanvasProps extends CanvasComponentProps<DashboardContent> {}

/** Mock chart component */
function MockChart({ type, title }: { type: string; title: string }) {
  return (
    <div className={styles.mockChart}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartType}>{type}</span>
      </div>
      <div className={styles.chartBody}>
        {type === 'bar' && (
          <div className={styles.barChart}>
            {[65, 80, 45, 90, 70].map((height, idx) => (
              <div
                key={idx}
                className={styles.bar}
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
        )}
        {type === 'line' && (
          <svg className={styles.lineChart} viewBox="0 0 100 50" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke="var(--color-primary-500, #6366f1)"
              strokeWidth="2"
              points="0,40 20,25 40,35 60,15 80,20 100,10"
            />
          </svg>
        )}
        {type === 'pie' && (
          <svg className={styles.pieChart} viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="var(--color-primary-200, #c7d2fe)" />
            <path
              d="M 50 50 L 50 10 A 40 40 0 0 1 85 65 Z"
              fill="var(--color-primary-500, #6366f1)"
            />
            <path
              d="M 50 50 L 85 65 A 40 40 0 0 1 25 75 Z"
              fill="var(--color-primary-400, #818cf8)"
            />
          </svg>
        )}
        {type === 'area' && (
          <svg className={styles.areaChart} viewBox="0 0 100 50" preserveAspectRatio="none">
            <path
              fill="var(--color-primary-100, #e0e7ff)"
              d="M 0,50 L 0,40 20,25 40,35 60,15 80,20 100,10 100,50 Z"
            />
            <polyline
              fill="none"
              stroke="var(--color-primary-500, #6366f1)"
              strokeWidth="2"
              points="0,40 20,25 40,35 60,15 80,20 100,10"
            />
          </svg>
        )}
      </div>
    </div>
  );
}

/** Metric widget */
function MetricWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const value = config.value as string | number || '—';
  const change = config.change as number | undefined;
  const unit = config.unit as string || '';

  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{title}</span>
      <span className={styles.metricValue}>
        {value}
        {unit && <span className={styles.metricUnit}>{unit}</span>}
      </span>
      {change !== undefined && (
        <span className={`${styles.metricChange} ${change >= 0 ? styles.positive : styles.negative}`}>
          {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
        </span>
      )}
    </div>
  );
}

/** Table widget */
function TableWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const headers = (config.headers as string[]) || ['Column 1', 'Column 2', 'Column 3'];
  const rows = (config.rows as string[][]) || [
    ['Data 1', 'Data 2', 'Data 3'],
    ['Data 4', 'Data 5', 'Data 6'],
  ];

  return (
    <div className={styles.tableWidget}>
      <div className={styles.tableHeader}>{title}</div>
      <table className={styles.table}>
        <thead>
          <tr>
            {headers.map((h, idx) => (
              <th key={idx}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx}>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Text widget */
function TextWidget({ title, config }: { title: string; config: Record<string, unknown> }) {
  const content = (config.content as string) || 'No content';

  return (
    <div className={styles.textWidget}>
      <div className={styles.textHeader}>{title}</div>
      <div className={styles.textContent}>{content}</div>
    </div>
  );
}

/** Render a widget based on its type */
function renderWidget(widget: DashboardWidget) {
  switch (widget.type) {
    case 'chart':
      return (
        <MockChart
          title={widget.title}
          type={(widget.config.chartType as string) || 'bar'}
        />
      );
    case 'metric':
      return <MetricWidget title={widget.title} config={widget.config} />;
    case 'table':
      return <TableWidget title={widget.title} config={widget.config} />;
    case 'text':
      return <TextWidget title={widget.title} config={widget.config} />;
    default:
      return (
        <div className={styles.unknownWidget}>
          <span>Unknown widget type: {widget.type}</span>
        </div>
      );
  }
}

export function DashboardCanvas({
  artifact,
  className,
}: DashboardCanvasProps) {
  const { widgets, gridColumns = 12 } = artifact.content;

  // If no widgets, show empty state
  if (widgets.length === 0) {
    return (
      <div className={`${styles.container} ${className ?? ''}`}>
        <div className={styles.emptyState}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="7" height="9" rx="1" />
            <rect x="14" y="3" width="7" height="5" rx="1" />
            <rect x="14" y="12" width="7" height="9" rx="1" />
            <rect x="3" y="16" width="7" height="5" rx="1" />
          </svg>
          <h3>No widgets yet</h3>
          <p>Add charts, metrics, and tables to build your dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      <div
        className={styles.grid}
        style={{
          gridTemplateColumns: `repeat(${gridColumns}, 1fr)`,
        }}
      >
        {widgets.map(widget => (
          <div
            key={widget.id}
            className={styles.widgetContainer}
            style={{
              gridColumn: `${widget.x + 1} / span ${widget.width}`,
              gridRow: `${widget.y + 1} / span ${widget.height}`,
            }}
          >
            {renderWidget(widget)}
          </div>
        ))}
      </div>
    </div>
  );
}
