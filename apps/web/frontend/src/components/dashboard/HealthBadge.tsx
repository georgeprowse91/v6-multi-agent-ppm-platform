import styles from './HealthBadge.module.css';

type HealthStatus = 'healthy' | 'atRisk' | 'critical' | 'unknown';
type TrendDirection = 'improving' | 'stable' | 'declining' | 'rapidly_declining';
type BadgeSize = 'sm' | 'md' | 'lg';

interface SignalBreakdown {
  risk_score?: number;
  schedule_score?: number;
  budget_score?: number;
  resource_score?: number;
}

export interface HealthBadgeProps {
  /** Health score value between 0 and 1 */
  score: number;
  /** Trend direction */
  trend?: TrendDirection | string;
  /** Optional signal breakdown for tooltip */
  breakdown?: SignalBreakdown;
  /** Size variant */
  size?: BadgeSize;
  /** Show tooltip on hover */
  showTooltip?: boolean;
  /** Additional CSS class */
  className?: string;
}

function resolveStatus(score: number): HealthStatus {
  if (score >= 0.7) return 'healthy';
  if (score >= 0.4) return 'atRisk';
  if (score > 0) return 'critical';
  return 'unknown';
}

function trendArrow(trend: string): string {
  switch (trend) {
    case 'improving':
      return '\u2191';
    case 'declining':
      return '\u2193';
    case 'rapidly_declining':
      return '\u21CA';
    default:
      return '\u2192';
  }
}

function trendLabel(trend: string): string {
  switch (trend) {
    case 'improving':
      return 'Improving';
    case 'declining':
      return 'Declining';
    case 'rapidly_declining':
      return 'Rapidly declining';
    default:
      return 'Stable';
  }
}

function trendStyle(trend: string): string {
  switch (trend) {
    case 'improving':
      return styles.improving;
    case 'declining':
      return styles.declining;
    case 'rapidly_declining':
      return styles.rapidlyDeclining;
    default:
      return styles.stable;
  }
}

function signalColor(value: number): string {
  if (value >= 0.7) return '#22c55e';
  if (value >= 0.4) return '#eab308';
  return '#ef4444';
}

function SignalTooltip({ score, trend, breakdown }: { score: number; trend?: string; breakdown?: SignalBreakdown }) {
  const signals = [
    { key: 'risk_score', label: 'Risk' },
    { key: 'schedule_score', label: 'Schedule' },
    { key: 'budget_score', label: 'Budget' },
    { key: 'resource_score', label: 'Resource' },
  ] as const;

  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipRow}>
        <span className={styles.tooltipLabel}>Composite</span>
        <span className={styles.tooltipValue}>{Math.round(score * 100)}%</span>
      </div>
      {trend && (
        <div className={styles.tooltipRow}>
          <span className={styles.tooltipLabel}>Trend</span>
          <span className={styles.tooltipValue}>{trendLabel(trend)}</span>
        </div>
      )}
      {breakdown && (
        <div className={styles.signalBars}>
          {signals.map(({ key, label }) => {
            const value = breakdown[key] ?? 0;
            // Invert risk for display (lower risk = better health)
            const displayValue = key === 'risk_score' ? 1 - value : value;
            return (
              <div key={key} style={{ flex: 1 }}>
                <div className={styles.signalBar}>
                  <div
                    className={styles.signalBarFill}
                    style={{
                      width: `${Math.round(displayValue * 100)}%`,
                      background: signalColor(displayValue),
                    }}
                  />
                </div>
                <div className={styles.signalBarLabel}>{label}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function HealthBadge({
  score,
  trend,
  breakdown,
  size = 'md',
  showTooltip = true,
  className,
}: HealthBadgeProps) {
  const status = resolveStatus(score);
  const displayScore = Math.round(score * 100);

  const badgeClasses = [
    styles.badge,
    styles[status],
    size !== 'md' ? styles[size] : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const badge = (
    <span className={badgeClasses} role="status" aria-label={`Health score: ${displayScore}%`}>
      <span className={styles.scoreValue}>{displayScore}</span>
      {trend && (
        <span className={`${styles.trendArrow} ${trendStyle(trend)}`} aria-label={trendLabel(trend)}>
          {trendArrow(trend)}
        </span>
      )}
    </span>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <span className={styles.tooltipWrapper}>
      {badge}
      <SignalTooltip score={score} trend={trend} breakdown={breakdown} />
    </span>
  );
}

export default HealthBadge;
