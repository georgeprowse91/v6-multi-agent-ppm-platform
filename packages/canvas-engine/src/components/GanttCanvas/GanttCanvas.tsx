/**
 * GanttCanvas — Interactive Gantt chart with AI-assisted schedule optimisation.
 *
 * Merges tabular task editing with visual timeline bars, drag-to-reschedule,
 * SVG dependency connector lines, baseline comparison overlay, critical-path
 * highlighting, resource utilisation chart, and AI optimisation accept/reject UI.
 */

import { useMemo, useState, useRef, useCallback, useEffect } from 'react';
import type { CanvasComponentProps } from '../../types/canvas';
import type { GanttContent, GanttTask, OptimizationSuggestion } from '../../types/artifact';
import styles from './GanttCanvas.module.css';

export interface GanttCanvasProps extends CanvasComponentProps<GanttContent> {
  onRequestOptimization?: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function daysBetween(a: string, b: string): number {
  return Math.ceil(
    (new Date(b).getTime() - new Date(a).getTime()) / 86_400_000,
  );
}

function addDays(iso: string, n: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/* ------------------------------------------------------------------ */
/*  Critical-path (CPM) in-browser                                     */
/* ------------------------------------------------------------------ */

interface CpmResult {
  earlyStart: Record<string, number>;
  earlyFinish: Record<string, number>;
  lateStart: Record<string, number>;
  lateFinish: Record<string, number>;
  slack: Record<string, number>;
  critical: Set<string>;
}

function computeCpm(tasks: GanttTask[]): CpmResult {
  const taskMap = new Map(tasks.map(t => [t.id, t]));
  const duration = (t: GanttTask) => Math.max(daysBetween(t.startDate, t.endDate), 1);

  // Build adjacency
  const successors: Record<string, string[]> = {};
  const predecessors: Record<string, string[]> = {};
  for (const t of tasks) {
    successors[t.id] = [];
    predecessors[t.id] = [];
  }
  for (const t of tasks) {
    for (const dep of t.dependencies) {
      if (taskMap.has(dep)) {
        successors[dep].push(t.id);
        predecessors[t.id].push(dep);
      }
    }
  }

  // Topological sort (Kahn's)
  const inDeg: Record<string, number> = {};
  for (const t of tasks) inDeg[t.id] = predecessors[t.id].length;
  const queue = tasks.filter(t => inDeg[t.id] === 0).map(t => t.id);
  const order: string[] = [];
  while (queue.length) {
    const id = queue.shift()!;
    order.push(id);
    for (const s of successors[id]) {
      inDeg[s]--;
      if (inDeg[s] === 0) queue.push(s);
    }
  }

  // Forward pass
  const es: Record<string, number> = {};
  const ef: Record<string, number> = {};
  for (const id of order) {
    const preds = predecessors[id];
    es[id] = preds.length ? Math.max(...preds.map(p => ef[p])) : 0;
    ef[id] = es[id] + duration(taskMap.get(id)!);
  }

  // Backward pass
  const projectEnd = Math.max(...tasks.map(t => ef[t.id] ?? 0));
  const ls: Record<string, number> = {};
  const lf: Record<string, number> = {};
  for (let i = order.length - 1; i >= 0; i--) {
    const id = order[i];
    const succs = successors[id];
    lf[id] = succs.length ? Math.min(...succs.map(s => ls[s])) : projectEnd;
    ls[id] = lf[id] - duration(taskMap.get(id)!);
  }

  const slack: Record<string, number> = {};
  const critical = new Set<string>();
  for (const t of tasks) {
    slack[t.id] = ls[t.id] - es[t.id];
    if (slack[t.id] === 0) critical.add(t.id);
  }

  return { earlyStart: es, earlyFinish: ef, lateStart: ls, lateFinish: lf, slack, critical };
}

/** Cascade dependent tasks forward when a task is dragged */
function cascadeDependencies(tasks: GanttTask[], movedId: string, deltaDays: number): GanttTask[] {
  const taskMap = new Map(tasks.map(t => [t.id, { ...t }]));
  const visited = new Set<string>();

  function propagate(id: string) {
    if (visited.has(id)) return;
    visited.add(id);
    const task = taskMap.get(id)!;
    // Find all dependents
    for (const [, t] of taskMap) {
      if (t.dependencies.includes(id)) {
        const predEnd = new Date(task.endDate).getTime();
        const depStart = new Date(t.startDate).getTime();
        if (depStart < predEnd) {
          const shift = Math.ceil((predEnd - depStart) / 86_400_000);
          t.startDate = addDays(t.startDate, shift);
          t.endDate = addDays(t.endDate, shift);
          propagate(t.id);
        }
      }
    }
  }

  const moved = taskMap.get(movedId);
  if (moved) {
    moved.startDate = addDays(moved.startDate, deltaDays);
    moved.endDate = addDays(moved.endDate, deltaDays);
    propagate(movedId);
  }
  return Array.from(taskMap.values());
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

interface BarProps {
  task: GanttTask;
  viewStart: Date;
  totalDays: number;
  isCritical: boolean;
  showBaseline: boolean;
  rowIndex: number;
  onDragStart: (id: string, x: number) => void;
  readOnly: boolean;
}

function GanttBar({ task, viewStart, totalDays, isCritical, showBaseline, onDragStart, readOnly }: BarProps) {
  const startOff = Math.max(0, (new Date(task.startDate).getTime() - viewStart.getTime()) / 86_400_000);
  const dur = Math.max(daysBetween(task.startDate, task.endDate), 1);
  const left = (startOff / totalDays) * 100;
  const width = (dur / totalDays) * 100;

  let baselineEl: React.ReactNode = null;
  if (showBaseline && task.baselineStart && task.baselineEnd) {
    const bOff = Math.max(0, (new Date(task.baselineStart).getTime() - viewStart.getTime()) / 86_400_000);
    const bDur = Math.max(daysBetween(task.baselineStart, task.baselineEnd), 1);
    baselineEl = (
      <div
        className={styles.baselineBar}
        style={{ left: `${(bOff / totalDays) * 100}%`, width: `${(bDur / totalDays) * 100}%` }}
        title={`Baseline: ${fmtDate(task.baselineStart)} – ${fmtDate(task.baselineEnd)}`}
      />
    );
  }

  const barColor = isCritical
    ? 'var(--color-state-error-fg, #ef4444)'
    : task.color || 'var(--color-dataviz-series-primary, #3b82f6)';

  return (
    <div className={styles.trackCell}>
      {baselineEl}
      <div
        className={`${styles.bar} ${isCritical ? styles.barCritical : ''}`}
        style={{ left: `${left}%`, width: `${Math.max(width, 1.5)}%`, backgroundColor: barColor }}
        title={`${task.name}: ${fmtDate(task.startDate)} – ${fmtDate(task.endDate)}${task.slack !== undefined ? ` (slack ${task.slack}d)` : ''}`}
        role={readOnly ? 'img' : 'slider'}
        aria-label={`Gantt bar for ${task.name}`}
        onMouseDown={readOnly ? undefined : (e) => onDragStart(task.id, e.clientX)}
      >
        {task.progress !== undefined && (
          <div className={styles.progress} style={{ width: `${task.progress}%` }} />
        )}
        {task.isMilestone && <div className={styles.milestone}>◆</div>}
      </div>
    </div>
  );
}

interface SvgArrowsProps {
  tasks: GanttTask[];
  viewStart: Date;
  totalDays: number;
  rowHeight: number;
  trackWidth: number;
  labelWidth: number;
}

function DependencyArrows({ tasks, viewStart, totalDays, rowHeight, trackWidth }: SvgArrowsProps) {
  const taskIndex = new Map(tasks.map((t, i) => [t.id, i]));
  const arrows: React.ReactNode[] = [];

  for (const task of tasks) {
    const toIdx = taskIndex.get(task.id);
    if (toIdx === undefined) continue;
    for (const dep of task.dependencies) {
      const fromIdx = taskIndex.get(dep);
      if (fromIdx === undefined) continue;
      const fromTask = tasks[fromIdx];

      const fromEndOff = (new Date(fromTask.endDate).getTime() - viewStart.getTime()) / 86_400_000;
      const toStartOff = (new Date(task.startDate).getTime() - viewStart.getTime()) / 86_400_000;

      const x1 = (fromEndOff / totalDays) * trackWidth;
      const y1 = fromIdx * rowHeight + rowHeight / 2;
      const x2 = (toStartOff / totalDays) * trackWidth;
      const y2 = toIdx * rowHeight + rowHeight / 2;

      const midX = x1 + (x2 - x1) * 0.5;

      arrows.push(
        <g key={`${dep}->${task.id}`}>
          <path
            d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
            fill="none"
            stroke="var(--color-neutral-400, #a3a3a3)"
            strokeWidth="1.5"
            markerEnd="url(#arrowhead)"
          />
        </g>,
      );
    }
  }

  if (!arrows.length) return null;

  return (
    <svg className={styles.arrowSvg} style={{ width: trackWidth, height: tasks.length * rowHeight }}>
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="var(--color-neutral-500, #737373)" />
        </marker>
      </defs>
      {arrows}
    </svg>
  );
}

interface OptimizationPanelProps {
  suggestions: OptimizationSuggestion[];
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onRequestOptimization?: () => void;
  readOnly: boolean;
}

function OptimizationPanel({ suggestions, onAccept, onReject, onRequestOptimization, readOnly }: OptimizationPanelProps) {
  const pending = suggestions.filter(s => s.status === 'pending');
  const accepted = suggestions.filter(s => s.status === 'accepted');
  const rejected = suggestions.filter(s => s.status === 'rejected');

  return (
    <div className={styles.optimizationPanel}>
      <div className={styles.optimizationHeader}>
        <h4 className={styles.optimizationTitle}>AI Schedule Optimisation</h4>
        {!readOnly && onRequestOptimization && (
          <button className={styles.suggestBtn} onClick={onRequestOptimization}>
            Suggest optimal schedule
          </button>
        )}
      </div>

      {pending.length > 0 && (
        <div className={styles.suggestionSection}>
          <h5 className={styles.suggestionSectionTitle}>Pending Suggestions</h5>
          {pending.map(s => (
            <div key={s.id} className={styles.suggestionCard}>
              <div className={styles.suggestionInfo}>
                <span className={`${styles.suggestionType} ${styles[`type_${s.type}`] || ''}`}>{s.type.replace(/_/g, ' ')}</span>
                <p className={styles.suggestionDesc}>{s.description}</p>
                <span className={styles.savingBadge}>Save ~{s.projectedSavingDays}d</span>
              </div>
              {!readOnly && (
                <div className={styles.suggestionActions}>
                  <button className={styles.acceptBtn} onClick={() => onAccept(s.id)}>Accept</button>
                  <button className={styles.rejectBtn} onClick={() => onReject(s.id)}>Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {accepted.length > 0 && (
        <div className={styles.suggestionSection}>
          <h5 className={styles.suggestionSectionTitle}>Accepted ({accepted.length})</h5>
          {accepted.map(s => (
            <div key={s.id} className={`${styles.suggestionCard} ${styles.suggestionAccepted}`}>
              <span className={styles.suggestionDesc}>{s.description}</span>
              <span className={styles.statusBadge}>Accepted</span>
            </div>
          ))}
        </div>
      )}

      {rejected.length > 0 && (
        <div className={styles.suggestionSection}>
          <h5 className={styles.suggestionSectionTitle}>Rejected ({rejected.length})</h5>
          {rejected.map(s => (
            <div key={s.id} className={`${styles.suggestionCard} ${styles.suggestionRejected}`}>
              <span className={styles.suggestionDesc}>{s.description}</span>
              <span className={styles.statusBadge}>Rejected</span>
            </div>
          ))}
        </div>
      )}

      {suggestions.length === 0 && (
        <p className={styles.noSuggestions}>
          No optimisation suggestions yet. Click &ldquo;Suggest optimal schedule&rdquo; to analyse.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Resource Utilisation Chart                                         */
/* ------------------------------------------------------------------ */

interface ResourceChartProps {
  utilization: GanttContent['resourceUtilization'];
}

function ResourceLevelChart({ utilization }: ResourceChartProps) {
  if (!utilization?.length) {
    return (
      <div className={styles.resourcePanel}>
        <h4 className={styles.optimizationTitle}>Resource Utilisation</h4>
        <p className={styles.noSuggestions}>No resource utilisation data available.</p>
      </div>
    );
  }

  return (
    <div className={styles.resourcePanel}>
      <h4 className={styles.optimizationTitle}>Resource Utilisation</h4>
      {utilization.map(res => {
        const maxPercent = Math.max(...res.dailyUtilization.map(d => d.percent), 100);
        return (
          <div key={res.resourceId} className={styles.resourceRow}>
            <span className={styles.resourceName}>{res.resourceName}</span>
            <div className={styles.resourceBars}>
              {res.dailyUtilization.map(d => {
                const h = Math.max((d.percent / maxPercent) * 40, 2);
                const over = d.percent > 100;
                return (
                  <div
                    key={d.date}
                    className={`${styles.resourceBar} ${over ? styles.resourceBarOver : ''}`}
                    style={{ height: `${h}px` }}
                    title={`${d.date}: ${d.percent}%`}
                  />
                );
              })}
            </div>
            <span className={styles.resourceAvg}>
              {Math.round(res.dailyUtilization.reduce((s, d) => s + d.percent, 0) / res.dailyUtilization.length)}% avg
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

const ROW_HEIGHT = 48;
const LABEL_WIDTH = 220;

export function GanttCanvas({ artifact, onChange, readOnly = false, className, onRequestOptimization }: GanttCanvasProps) {
  const {
    tasks,
    viewStart: viewStartStr,
    viewEnd: viewEndStr,
    optimizationSuggestions = [],
    resourceUtilization,
    showBaseline = false,
    showCriticalPath = true,
    showResourceChart = false,
  } = artifact.content;

  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragOrigDates, setDragOrigDates] = useState<{ start: string; end: string } | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'table'>('timeline');
  const trackRef = useRef<HTMLDivElement>(null);

  // CPM
  const cpm = useMemo(() => computeCpm(tasks), [tasks]);

  // Annotate tasks with CPM results
  const annotatedTasks = useMemo(() =>
    tasks.map(t => ({
      ...t,
      isCritical: cpm.critical.has(t.id),
      slack: cpm.slack[t.id] ?? 0,
    })),
  [tasks, cpm]);

  // View range calculation
  const { viewStart, viewEnd, totalDays, monthHeaders } = useMemo(() => {
    let start: Date;
    let end: Date;

    if (viewStartStr && viewEndStr) {
      start = new Date(viewStartStr);
      end = new Date(viewEndStr);
    } else if (tasks.length > 0) {
      const allDates = tasks.flatMap(t => {
        const dates = [new Date(t.startDate), new Date(t.endDate)];
        if (t.baselineStart) dates.push(new Date(t.baselineStart));
        if (t.baselineEnd) dates.push(new Date(t.baselineEnd));
        return dates;
      });
      start = new Date(Math.min(...allDates.map(d => d.getTime())));
      end = new Date(Math.max(...allDates.map(d => d.getTime())));
      start.setDate(start.getDate() - 7);
      end.setDate(end.getDate() + 14);
    } else {
      start = new Date();
      start.setDate(1);
      end = new Date();
      end.setMonth(end.getMonth() + 3);
    }

    const days = Math.max(daysBetween(toDateStr(start), toDateStr(end)), 1);

    const months: { label: string; startPercent: number; widthPercent: number }[] = [];
    const cur = new Date(start);
    cur.setDate(1);
    while (cur <= end) {
      const ms = new Date(cur);
      const me = new Date(cur.getFullYear(), cur.getMonth() + 1, 0);
      const effS = ms < start ? start : ms;
      const effE = me > end ? end : me;
      const sOff = daysBetween(toDateStr(start), toDateStr(effS));
      const dur = daysBetween(toDateStr(effS), toDateStr(effE));
      months.push({
        label: ms.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
        startPercent: (sOff / days) * 100,
        widthPercent: (dur / days) * 100,
      });
      cur.setMonth(cur.getMonth() + 1);
    }

    return { viewStart: start, viewEnd: end, totalDays: days, monthHeaders: months };
  }, [tasks, viewStartStr, viewEndStr]);

  // Drag handlers
  const handleDragStart = useCallback((id: string, x: number) => {
    if (readOnly) return;
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    setDraggingId(id);
    setDragStartX(x);
    setDragOrigDates({ start: task.startDate, end: task.endDate });
  }, [readOnly, tasks]);

  useEffect(() => {
    if (!draggingId || !dragOrigDates) return;

    const handleMouseMove = (e: MouseEvent) => {
      const tw = trackRef.current?.getBoundingClientRect().width;
      if (!tw) return;
      const dx = e.clientX - dragStartX;
      const deltaDays = Math.round((dx / tw) * totalDays);
      if (deltaDays === 0 || !onChange) return;

      const newTasks = cascadeDependencies(
        tasks.map(t => t.id === draggingId ? { ...t, startDate: dragOrigDates.start, endDate: dragOrigDates.end } : t),
        draggingId,
        deltaDays,
      );
      onChange({ ...artifact.content, tasks: newTasks });
    };

    const handleMouseUp = () => {
      setDraggingId(null);
      setDragOrigDates(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggingId, dragOrigDates, dragStartX, totalDays, onChange, tasks, artifact.content]);

  // Task CRUD helpers
  const updateTask = useCallback((id: string, patch: Partial<GanttTask>) => {
    if (!onChange) return;
    onChange({ ...artifact.content, tasks: tasks.map(t => t.id === id ? { ...t, ...patch } : t) });
  }, [onChange, tasks, artifact.content]);

  const addTask = useCallback(() => {
    if (readOnly || !onChange) return;
    const today = new Date().toISOString().slice(0, 10);
    const newTask: GanttTask = {
      id: `task-${Date.now()}`,
      name: 'New task',
      startDate: today,
      endDate: addDays(today, 5),
      dependencies: [],
      progress: 0,
    };
    onChange({ ...artifact.content, tasks: [...tasks, newTask] });
  }, [readOnly, onChange, tasks, artifact.content]);

  const removeTask = useCallback((id: string) => {
    if (readOnly || !onChange) return;
    onChange({
      ...artifact.content,
      tasks: tasks.filter(t => t.id !== id).map(t => ({
        ...t,
        dependencies: t.dependencies.filter(d => d !== id),
      })),
    });
  }, [readOnly, onChange, tasks, artifact.content]);

  // Optimization actions
  const handleAcceptSuggestion = useCallback((suggestionId: string) => {
    if (!onChange) return;
    const updated = (artifact.content.optimizationSuggestions ?? []).map(s =>
      s.id === suggestionId ? { ...s, status: 'accepted' as const } : s,
    );
    onChange({ ...artifact.content, optimizationSuggestions: updated });
  }, [onChange, artifact.content]);

  const handleRejectSuggestion = useCallback((suggestionId: string) => {
    if (!onChange) return;
    const updated = (artifact.content.optimizationSuggestions ?? []).map(s =>
      s.id === suggestionId ? { ...s, status: 'rejected' as const } : s,
    );
    onChange({ ...artifact.content, optimizationSuggestions: updated });
  }, [onChange, artifact.content]);

  // Toggle helpers
  const toggleBaseline = useCallback(() => {
    onChange?.({ ...artifact.content, showBaseline: !showBaseline });
  }, [onChange, artifact.content, showBaseline]);

  const toggleCriticalPath = useCallback(() => {
    onChange?.({ ...artifact.content, showCriticalPath: !showCriticalPath });
  }, [onChange, artifact.content, showCriticalPath]);

  const toggleResourceChart = useCallback(() => {
    onChange?.({ ...artifact.content, showResourceChart: !showResourceChart });
  }, [onChange, artifact.content, showResourceChart]);

  // Track width for SVG arrows
  const [trackWidth, setTrackWidth] = useState(800);
  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      for (const entry of entries) setTrackWidth(entry.contentRect.width);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div className={`${styles.container} ${className ?? ''}`}>
      {/* Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.tabGroup}>
          <button
            className={`${styles.tab} ${activeTab === 'timeline' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('timeline')}
          >
            Timeline
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'table' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('table')}
          >
            Table
          </button>
        </div>
        <div className={styles.toolbarActions}>
          <label className={styles.toggle}>
            <input type="checkbox" checked={showBaseline} onChange={toggleBaseline} />
            Baseline
          </label>
          <label className={styles.toggle}>
            <input type="checkbox" checked={showCriticalPath} onChange={toggleCriticalPath} />
            Critical Path
          </label>
          <label className={styles.toggle}>
            <input type="checkbox" checked={showResourceChart} onChange={toggleResourceChart} />
            Resources
          </label>
          {!readOnly && <button className={styles.addBtn} onClick={addTask}>+ Add Task</button>}
        </div>
      </div>

      {/* Timeline view */}
      {activeTab === 'timeline' && (
        <>
          {/* Month headers */}
          <div className={styles.headerRow}>
            <div className={styles.headerLabel}>Tasks</div>
            <div className={styles.headerTimeline}>
              {monthHeaders.map((m, i) => (
                <div key={i} className={styles.monthHeader} style={{ left: `${m.startPercent}%`, width: `${m.widthPercent}%` }}>
                  {m.label}
                </div>
              ))}
            </div>
          </div>

          {/* Body */}
          <div className={styles.body}>
            {annotatedTasks.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No tasks yet. Click &ldquo;+ Add Task&rdquo; to create one.</p>
              </div>
            ) : (
              <div className={styles.rowsContainer}>
                {/* Task rows */}
                {annotatedTasks.map((task, idx) => (
                  <div
                    key={task.id}
                    className={`${styles.row} ${task.isCritical && showCriticalPath ? styles.rowCritical : ''} ${editingTaskId === task.id ? styles.rowEditing : ''}`}
                    style={{ height: ROW_HEIGHT }}
                  >
                    <div
                      className={styles.rowLabel}
                      onClick={() => setEditingTaskId(editingTaskId === task.id ? null : task.id)}
                      title="Click to edit"
                    >
                      <span className={styles.taskName}>{task.name}</span>
                      <span className={styles.taskDates}>
                        {fmtDate(task.startDate)} – {fmtDate(task.endDate)}
                      </span>
                      {task.isCritical && showCriticalPath && <span className={styles.criticalBadge}>Critical</span>}
                    </div>
                    <div className={styles.rowTrack} ref={idx === 0 ? trackRef : undefined}>
                      <GanttBar
                        task={task}
                        viewStart={viewStart}
                        totalDays={totalDays}
                        isCritical={!!(task.isCritical && showCriticalPath)}
                        showBaseline={showBaseline}
                        rowIndex={idx}
                        onDragStart={handleDragStart}
                        readOnly={readOnly}
                      />
                    </div>
                  </div>
                ))}

                {/* SVG dependency arrows overlay */}
                <div className={styles.arrowOverlay} style={{ left: LABEL_WIDTH }}>
                  <DependencyArrows
                    tasks={annotatedTasks}
                    viewStart={viewStart}
                    totalDays={totalDays}
                    rowHeight={ROW_HEIGHT}
                    trackWidth={trackWidth}
                    labelWidth={LABEL_WIDTH}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Inline edit panel */}
          {editingTaskId && !readOnly && (
            <div className={styles.editPanel}>
              {(() => {
                const t = tasks.find(tk => tk.id === editingTaskId);
                if (!t) return null;
                return (
                  <>
                    <h5 className={styles.editTitle}>Edit Task</h5>
                    <div className={styles.editGrid}>
                      <label>Name
                        <input value={t.name} onChange={e => updateTask(t.id, { name: e.target.value })} />
                      </label>
                      <label>Start
                        <input type="date" value={t.startDate} onChange={e => updateTask(t.id, { startDate: e.target.value })} />
                      </label>
                      <label>End
                        <input type="date" value={t.endDate} onChange={e => updateTask(t.id, { endDate: e.target.value })} />
                      </label>
                      <label>Progress (%)
                        <input type="number" min={0} max={100} value={t.progress ?? 0} onChange={e => updateTask(t.id, { progress: Number(e.target.value) })} />
                      </label>
                      <label>Baseline Start
                        <input type="date" value={t.baselineStart ?? ''} onChange={e => updateTask(t.id, { baselineStart: e.target.value || undefined })} />
                      </label>
                      <label>Baseline End
                        <input type="date" value={t.baselineEnd ?? ''} onChange={e => updateTask(t.id, { baselineEnd: e.target.value || undefined })} />
                      </label>
                      <label>Dependencies (comma-separated IDs)
                        <input value={t.dependencies.join(', ')} onChange={e => updateTask(t.id, { dependencies: e.target.value.split(',').map(v => v.trim()).filter(Boolean) })} />
                      </label>
                      <label>Resource ID
                        <input value={t.resourceId ?? ''} onChange={e => updateTask(t.id, { resourceId: e.target.value || undefined })} />
                      </label>
                    </div>
                    <div className={styles.editActions}>
                      <button className={styles.deleteBtn} onClick={() => { removeTask(t.id); setEditingTaskId(null); }}>Delete Task</button>
                      <button className={styles.closeEditBtn} onClick={() => setEditingTaskId(null)}>Close</button>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </>
      )}

      {/* Table view */}
      {activeTab === 'table' && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Start</th>
                <th>End</th>
                <th>Progress</th>
                <th>Dependencies</th>
                <th>Baseline Start</th>
                <th>Baseline End</th>
                <th>Slack</th>
                <th>Critical</th>
                {!readOnly && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {annotatedTasks.map(t => (
                <tr key={t.id} className={t.isCritical && showCriticalPath ? styles.rowCritical : ''}>
                  <td><input className={styles.cellInput} value={t.name} readOnly={readOnly} onChange={e => updateTask(t.id, { name: e.target.value })} /></td>
                  <td><input className={styles.cellInput} type="date" value={t.startDate} readOnly={readOnly} onChange={e => updateTask(t.id, { startDate: e.target.value })} /></td>
                  <td><input className={styles.cellInput} type="date" value={t.endDate} readOnly={readOnly} onChange={e => updateTask(t.id, { endDate: e.target.value })} /></td>
                  <td><input className={styles.cellInput} type="number" min={0} max={100} value={t.progress ?? 0} readOnly={readOnly} onChange={e => updateTask(t.id, { progress: Number(e.target.value) })} /></td>
                  <td><input className={styles.cellInput} value={t.dependencies.join(', ')} readOnly={readOnly} onChange={e => updateTask(t.id, { dependencies: e.target.value.split(',').map(v => v.trim()).filter(Boolean) })} /></td>
                  <td><input className={styles.cellInput} type="date" value={t.baselineStart ?? ''} readOnly={readOnly} onChange={e => updateTask(t.id, { baselineStart: e.target.value || undefined })} /></td>
                  <td><input className={styles.cellInput} type="date" value={t.baselineEnd ?? ''} readOnly={readOnly} onChange={e => updateTask(t.id, { baselineEnd: e.target.value || undefined })} /></td>
                  <td className={styles.slackCell}>{t.slack ?? '-'}d</td>
                  <td>{t.isCritical ? <span className={styles.criticalBadge}>Yes</span> : 'No'}</td>
                  {!readOnly && (
                    <td><button className={styles.deleteBtn} onClick={() => removeTask(t.id)}>Remove</button></td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Resource utilisation chart */}
      {showResourceChart && <ResourceLevelChart utilization={resourceUtilization} />}

      {/* Optimisation panel */}
      <OptimizationPanel
        suggestions={optimizationSuggestions}
        onAccept={handleAcceptSuggestion}
        onReject={handleRejectSuggestion}
        onRequestOptimization={onRequestOptimization}
        readOnly={readOnly}
      />

      {/* Footer */}
      <div className={styles.footer}>
        <span className={styles.footerInfo}>
          {tasks.length} task{tasks.length !== 1 ? 's' : ''}
          {showCriticalPath ? ` | ${cpm.critical.size} critical` : ''}
          {' | '}
          {fmtDate(toDateStr(viewStart))} – {fmtDate(toDateStr(viewEnd))}
        </span>
      </div>
    </div>
  );
}
