import { useEffect, useMemo, useState, type DragEvent, type KeyboardEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { KpiWidget } from '@/components/dashboard/KpiWidget';
import { StatusIndicator } from '@/components/dashboard/StatusIndicator';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAppStore, type EntitySelection } from '@/store';
import styles from './WorkspacePage.module.css';

type EntityType = 'portfolio' | 'program' | 'project';

interface WorkspacePageProps {
  type: EntityType;
}

interface DemandStage {
  stage: string;
  count: number;
  target: number;
  trend?: 'up' | 'down' | 'steady';
}

interface PipelineItem {
  item_id: string;
  title: string;
  summary: string;
  sponsor: string;
  priority: 'High' | 'Medium' | 'Low';
  type: 'intake' | 'project';
  status: string;
}

interface PipelineBoard {
  stages: string[];
  items: PipelineItem[];
}

interface KpiMetric {
  label: string;
  value: string;
  delta?: string;
}

interface CharterSnapshot {
  id: string;
  name: string;
  owner: string;
  status: string;
  updated: string;
}

interface WbsItem {
  name: string;
  children: string[];
}

interface RequirementItem {
  id: string;
  title: string;
  priority: string;
  status: string;
}

interface RiskItem {
  id: string;
  title: string;
  severity: string;
  owner: string;
}

interface IssueItem {
  id: string;
  title: string;
  status: string;
  owner: string;
}

interface HealthMetric {
  label: string;
  value: string;
  status: string;
}

interface HolisticInsight {
  id: string;
  title: string;
  summary: string;
  impact: 'High' | 'Medium' | 'Low';
  recommendation: string;
  confidence: string;
}

interface RelatedItem {
  id: string;
  name: string;
  status?: string;
  owner?: string;
}

interface DashboardPayload {
  kpis: KpiMetric[];
  pipeline: DemandStage[];
  charters: CharterSnapshot[];
  wbs: WbsItem[];
  requirements: RequirementItem[];
  risks: RiskItem[];
  issues: IssueItem[];
  healthMetrics: HealthMetric[];
  relatedItems: RelatedItem[];
  relatedItemsLimit?: number;
}

interface ScenarioSnapshot {
  id: string;
  label: string;
  summary: string;
  schedule: string;
  budget: string;
  forecast: string;
  variance: string;
  tone: 'positive' | 'neutral' | 'negative';
}

const API_BASE = '/api';
const RELATED_PAGE_SIZES = [5, 10, 20];

const typeLabels: Record<EntityType, string> = {
  portfolio: 'Portfolio',
  program: 'Program',
  project: 'Project',
};

const typeDescriptions: Record<EntityType, string> = {
  portfolio:
    'Strategic investment decisions and portfolio-level performance tracking.',
  program:
    'Coordination of related projects to achieve strategic objectives.',
  project: 'Execution of specific deliverables with defined scope and timeline.',
};

const emptyDashboard: DashboardPayload = {
  kpis: [],
  pipeline: [],
  charters: [],
  wbs: [],
  requirements: [],
  risks: [],
  issues: [],
  healthMetrics: [],
  relatedItems: [],
};

const endpointMap: Record<EntityType, string> = {
  portfolio: 'portfolios',
  program: 'programs',
  project: 'projects',
};

export function WorkspacePage({ type }: WorkspacePageProps) {
  const { portfolioId, programId, projectId } = useParams();
  const navigate = useNavigate();
  const { setCurrentSelection, currentActivity, addTab, openTabs, featureFlags } =
    useAppStore();

  const entityId = portfolioId || programId || projectId || 'unknown';
  const [entityName, setEntityName] = useState(entityId);
  const [dashboardData, setDashboardData] = useState<DashboardPayload>(emptyDashboard);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pipelineBoard, setPipelineBoard] = useState<PipelineBoard | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [pipelineSearch, setPipelineSearch] = useState('');
  const [pipelineSponsorFilter, setPipelineSponsorFilter] = useState('all');
  const [pipelinePriorityFilter, setPipelinePriorityFilter] = useState('all');
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  const [grabbedItemId, setGrabbedItemId] = useState<string | null>(null);
  const [grabbedCurrentStage, setGrabbedCurrentStage] = useState<string | null>(null);
  const [pipelineLiveMessage, setPipelineLiveMessage] = useState('');
  const [recentlyMovedPipelineItemId, setRecentlyMovedPipelineItemId] = useState<string | null>(null);
  const [relatedFilter, setRelatedFilter] = useState('');
  const [relatedPage, setRelatedPage] = useState(1);
  const [relatedPageSize, setRelatedPageSize] = useState(RELATED_PAGE_SIZES[0]);
  const scenarioModelingEnabled = featureFlags.scenario_modeling;
  const multiAgentCollabEnabled = featureFlags.multi_agent_collab === true;

  useEffect(() => {
    setEntityName(entityId);
  }, [entityId]);

  useEffect(() => {
    const selection: EntitySelection = {
      type,
      id: entityId,
      name: entityName || `${typeLabels[type]} ${entityId}`,
    };
    setCurrentSelection(selection);

    // Add a tab for this workspace if not already open
    const tabId = `${type}-${entityId}`;
    const existingTab = openTabs.find((t) => t.id === tabId);
    if (!existingTab) {
      addTab({
        id: tabId,
        title: `${typeLabels[type]}: ${entityId}`,
        type: 'dashboard',
        entityId,
      });
    }
  }, [type, entityId, entityName, setCurrentSelection, addTab, openTabs]);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchDashboard = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await fetch(
          `${API_BASE}/${endpointMap[type]}/${entityId}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          throw new Error(`Failed to load dashboard: ${response.statusText}`);
        }
        const data = await response.json();
        const payload = data.dashboard ?? data;
        if (!isMounted) return;
        setEntityName(payload.name ?? data.name ?? entityId);
        setDashboardData({
          kpis: payload.kpis ?? payload.kpiHighlights ?? [],
          pipeline: payload.pipeline ?? payload.demandPipeline ?? [],
          charters: payload.charters ?? payload.charterSnapshots ?? [],
          wbs: payload.wbs ?? payload.wbsSnapshot ?? [],
          requirements: payload.requirements ?? payload.requirementsSnapshot ?? [],
          risks: payload.risks ?? payload.riskSummary ?? [],
          issues: payload.issues ?? payload.issueSummary ?? [],
          healthMetrics: payload.healthMetrics ?? payload.health ?? [],
          relatedItems: payload.relatedItems ?? payload.programs ?? payload.projects ?? [],
          relatedItemsLimit: payload.relatedItemsLimit ?? payload.pageSize,
        });
        if (payload.relatedItemsLimit) {
          setRelatedPageSize(payload.relatedItemsLimit);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Failed to load dashboard data';
        setErrorMessage(message);
        setDashboardData(emptyDashboard);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    if (entityId !== 'unknown') {
      fetchDashboard();
    }

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [type, entityId]);

  useEffect(() => {
    setRelatedPage(1);
  }, [relatedFilter, relatedPageSize, dashboardData.relatedItems.length]);

  const supportsPipelineView = type === 'portfolio' || type === 'program';

  useEffect(() => {
    if (!supportsPipelineView || entityId === 'unknown') {
      setPipelineBoard(null);
      return;
    }

    let isMounted = true;
    const controller = new AbortController();

    const fetchPipeline = async () => {
      setPipelineLoading(true);
      setPipelineError(null);
      try {
        const response = await fetch(
          `${API_BASE}/pipeline/${type}/${entityId}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          throw new Error('Unable to load pipeline view.');
        }
        const payload = await response.json();
        if (!isMounted) return;
        setPipelineBoard(payload);
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Unable to load pipeline view.';
        setPipelineError(message);
        setPipelineBoard(null);
      } finally {
        if (isMounted) setPipelineLoading(false);
      }
    };

    fetchPipeline();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [supportsPipelineView, type, entityId]);

  useEffect(() => {
    setPipelineSearch('');
    setPipelineSponsorFilter('all');
    setPipelinePriorityFilter('all');
  }, [pipelineBoard?.items.length]);

  const relatedLabel = useMemo(() => {
    if (type === 'portfolio') return 'Programs';
    if (type === 'program') return 'Projects';
    return 'Related workstreams';
  }, [type]);

  const pageSizeOptions = useMemo(() => {
    const sizes = new Set(RELATED_PAGE_SIZES);
    sizes.add(relatedPageSize);
    return Array.from(sizes).sort((a, b) => a - b);
  }, [relatedPageSize]);

  const scenarioSnapshots = useMemo<ScenarioSnapshot[]>(() => {
    const baseBudget = type === 'project' ? '$2.45M' : '$24.5M';
    return [
      {
        id: 'baseline',
        label: 'Baseline',
        summary: 'Current approved plan and forecast.',
        schedule: '124 days',
        budget: baseBudget,
        forecast: baseBudget,
        variance: '0%',
        tone: 'neutral',
      },
      {
        id: 'best-case',
        label: 'Best case',
        summary: 'Aggressive recovery with additional resources.',
        schedule: '108 days',
        budget: baseBudget,
        forecast: type === 'project' ? '$2.38M' : '$23.8M',
        variance: '-3.0%',
        tone: 'positive',
      },
      {
        id: 'most-likely',
        label: 'Most likely',
        summary: 'Optimized sequencing with moderate buffer.',
        schedule: '132 days',
        budget: baseBudget,
        forecast: type === 'project' ? '$2.52M' : '$25.2M',
        variance: '2.8%',
        tone: 'neutral',
      },
      {
        id: 'worst-case',
        label: 'Worst case',
        summary: 'Vendor delay and late procurement.',
        schedule: '156 days',
        budget: baseBudget,
        forecast: type === 'project' ? '$2.74M' : '$27.4M',
        variance: '11.8%',
        tone: 'negative',
      },
    ];
  }, [type]);

  const holisticInsights = useMemo<HolisticInsight[]>(
    () => [
      {
        id: 'alignment',
        title: 'Strategic alignment uplift',
        summary:
          'Cross-agent signals indicate the portfolio is drifting from Q3 modernization objectives.',
        impact: 'High',
        recommendation: 'Rebalance 12% of discretionary spend toward cloud migration workstreams.',
        confidence: '0.78',
      },
      {
        id: 'capacity',
        title: 'Shared capacity pressure',
        summary:
          'Resource forecasts show delivery leads are exceeding capacity in the next two sprints.',
        impact: 'Medium',
        recommendation: 'Sequence vendor onboarding two weeks later to smooth peak utilization.',
        confidence: '0.72',
      },
      {
        id: 'governance',
        title: 'Governance gating risk',
        summary:
          'Compliance and finance agents flag missing artifacts for three in-flight initiatives.',
        impact: 'Low',
        recommendation: 'Schedule a joint checkpoint and pre-fill audit packets this week.',
        confidence: '0.66',
      },
    ],
    []
  );

  const filteredRelatedItems = useMemo(() => {
    if (!relatedFilter) return dashboardData.relatedItems;
    const lowered = relatedFilter.toLowerCase();
    return dashboardData.relatedItems.filter(
      (item) =>
        item.name.toLowerCase().includes(lowered) ||
        item.id.toLowerCase().includes(lowered) ||
        (item.status ?? '').toLowerCase().includes(lowered)
    );
  }, [dashboardData.relatedItems, relatedFilter]);

  const pipelineSponsors = useMemo(() => {
    const sponsors = new Set<string>();
    pipelineBoard?.items.forEach((item) => sponsors.add(item.sponsor));
    return Array.from(sponsors).sort();
  }, [pipelineBoard?.items]);

  const pipelinePriorities = useMemo(() => {
    const priorities = new Set<string>();
    pipelineBoard?.items.forEach((item) => priorities.add(item.priority));
    return Array.from(priorities).sort();
  }, [pipelineBoard?.items]);

  const filteredPipelineItems = useMemo(() => {
    if (!pipelineBoard) return [];
    const lowered = pipelineSearch.toLowerCase();
    return pipelineBoard.items.filter((item) => {
      const matchesSearch =
        !pipelineSearch ||
        item.title.toLowerCase().includes(lowered) ||
        item.summary.toLowerCase().includes(lowered) ||
        item.sponsor.toLowerCase().includes(lowered);
      const matchesSponsor =
        pipelineSponsorFilter === 'all' || item.sponsor === pipelineSponsorFilter;
      const matchesPriority =
        pipelinePriorityFilter === 'all' || item.priority === pipelinePriorityFilter;
      return matchesSearch && matchesSponsor && matchesPriority;
    });
  }, [pipelineBoard, pipelinePriorityFilter, pipelineSearch, pipelineSponsorFilter]);

  const pipelineItemsByStage = useMemo(() => {
    const grouped = new Map<string, PipelineItem[]>();
    if (!pipelineBoard) return grouped;
    pipelineBoard.stages.forEach((stage) => grouped.set(stage, []));
    filteredPipelineItems.forEach((item) => {
      const list = grouped.get(item.status) ?? [];
      list.push(item);
      grouped.set(item.status, list);
    });
    return grouped;
  }, [filteredPipelineItems, pipelineBoard]);

  const movePipelineItemToStage = async (
    board: PipelineBoard,
    itemId: string,
    stage: string
  ) => {
    const currentItem = board.items.find((item) => item.item_id === itemId);
    if (!currentItem || currentItem.status === stage) return;

    const optimisticItems = board.items.map((item) =>
      item.item_id === itemId ? { ...item, status: stage } : item
    );
    setPipelineBoard({ ...board, items: optimisticItems });
    setPipelineError(null);
    setRecentlyMovedPipelineItemId(itemId);

    try {
      const response = await fetch(
        `${API_BASE}/pipeline/${type}/${entityId}/items/${itemId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status: stage }),
        }
      );
      if (!response.ok) {
        throw new Error('Unable to update pipeline stage.');
      }
      window.setTimeout(() => {
        setRecentlyMovedPipelineItemId((current) => (current === itemId ? null : current));
      }, 200);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to update pipeline stage.';
      setPipelineError(message);
      setPipelineBoard(board);
      setRecentlyMovedPipelineItemId(null);
    }
  };

  const handlePipelineDrop = async (event: DragEvent<HTMLDivElement>, stage: string) => {
    event.preventDefault();
    const itemId = event.dataTransfer.getData('text/plain');
    if (!pipelineBoard || !itemId) return;
    await movePipelineItemToStage(pipelineBoard, itemId, stage);
    setDraggedItemId(null);
  };

  const handlePipelineDragStart = (event: DragEvent<HTMLDivElement>, itemId: string) => {
    event.dataTransfer.setData('text/plain', itemId);
    event.dataTransfer.effectAllowed = 'move';
    setDraggedItemId(itemId);
  };

  const handlePipelineDragEnd = () => {
    setDraggedItemId(null);
  };

  const handlePipelineItemKeyDown = async (
    event: KeyboardEvent<HTMLDivElement>,
    item: PipelineItem
  ) => {
    if (!pipelineBoard) return;
    const isGrabbed = grabbedItemId === item.item_id;

    if (!isGrabbed && (event.key === ' ' || event.key === 'Enter')) {
      event.preventDefault();
      setGrabbedItemId(item.item_id);
      setGrabbedCurrentStage(item.status);
      setPipelineLiveMessage(
        `Item ${item.title} grabbed. Use arrow keys to move between stages.`
      );
      return;
    }

    if (!isGrabbed) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      setGrabbedItemId(null);
      setGrabbedCurrentStage(null);
      setPipelineLiveMessage(`Move canceled for ${item.title}.`);
      return;
    }

    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      const currentStage = grabbedCurrentStage ?? item.status;
      const stageIndex = pipelineBoard.stages.indexOf(currentStage);
      if (stageIndex < 0) return;
      const nextIndex = event.key === 'ArrowLeft' ? stageIndex - 1 : stageIndex + 1;
      const nextStage = pipelineBoard.stages[nextIndex];
      if (!nextStage) return;
      setGrabbedCurrentStage(nextStage);
      setPipelineLiveMessage(
        `Item ${item.title} moved to ${nextStage}. Press Space to drop or Escape to cancel.`
      );
      return;
    }

    if (event.key === ' ') {
      event.preventDefault();
      const targetStage = grabbedCurrentStage ?? item.status;
      await movePipelineItemToStage(pipelineBoard, item.item_id, targetStage);
      setGrabbedItemId(null);
      setGrabbedCurrentStage(null);
      setPipelineLiveMessage(`Item ${item.title} dropped in ${targetStage}.`);
    }
  };

  const renderPipelineItem = (item: PipelineItem) => (
    <div
      key={item.item_id}
      className={`${styles.pipelineItem} ${grabbedItemId === item.item_id ? styles.pipelineItemGrabbed : ''} ${
        recentlyMovedPipelineItemId === item.item_id ? styles.pipelineItemMoved : ''
      }`}
      draggable
      tabIndex={0}
      role="listitem"
      aria-grabbed={grabbedItemId === item.item_id}
      onDragStart={(event) => handlePipelineDragStart(event, item.item_id)}
      onDragEnd={handlePipelineDragEnd}
      onKeyDown={(event) => void handlePipelineItemKeyDown(event, item)}
    >
      <div className={styles.pipelineItemHeader}>
        <span className={styles.pipelineItemType}>
          {item.type === 'intake' ? 'Intake request' : 'Active project'}
        </span>
        <span className={`${styles.badge} ${styles[`badge${item.priority}`]}`}>
          {item.priority}
        </span>
      </div>
      <div className={styles.pipelineItemTitle}>{item.title}</div>
      <p className={styles.pipelineItemSummary}>{item.summary}</p>
      <div className={styles.pipelineItemMeta}>Sponsor: {item.sponsor}</div>
      <label className={styles.pipelineMoveLabel}>
        Move to...
        <select
          className={styles.pipelineMoveSelect}
          aria-label={`Move ${item.title} to stage`}
          value={item.status}
          onChange={(event) => {
            if (!pipelineBoard) return;
            void movePipelineItemToStage(pipelineBoard, item.item_id, event.target.value);
          }}
        >
          {pipelineBoard?.stages.map((stage) => (
            <option key={`${item.item_id}-${stage}`} value={stage}>
              {stage}
            </option>
          ))}
        </select>
      </label>
    </div>
  );

  const relatedTotalPages = Math.max(
    1,
    Math.ceil(filteredRelatedItems.length / relatedPageSize)
  );
  const relatedPageStart = (relatedPage - 1) * relatedPageSize;
  const pagedRelatedItems = filteredRelatedItems.slice(
    relatedPageStart,
    relatedPageStart + relatedPageSize
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.badge}>{typeLabels[type]}</div>
        <h1 className={styles.title}>{entityName}</h1>
        <p className={styles.description}>{typeDescriptions[type]}</p>
      </header>

      <div className={styles.content}>
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Summary dashboard</h2>
              <p className={styles.sectionSubtitle}>
                Consolidated KPIs, health indicators, and executive highlights for this{' '}
                {typeLabels[type].toLowerCase()}.
              </p>
            </div>
            <button
              type="button"
              className={styles.primaryAction}
              onClick={() => navigate(`/projects/${encodeURIComponent(entityId)}/performance-dashboard`)}
              disabled={type !== 'project'}
            >
              View full dashboard
            </button>
          </div>
          <div
            className={styles.summaryGrid}
            aria-busy={isLoading}
            aria-live={isLoading ? 'off' : 'polite'}
          >
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div key={`kpi-skeleton-${index}`} className={styles.kpiSkeletonCard}>
                  <Skeleton variant="text" width="45%" />
                  <Skeleton variant="text" width="75%" height="1.8rem" />
                  <Skeleton variant="text" width="35%" />
                </div>
              ))
            ) : dashboardData.kpis.length > 0 ? (
              dashboardData.kpis.map((kpi) => (
                <KpiWidget
                  key={kpi.label}
                  label={kpi.label}
                  value={kpi.value}
                  delta={kpi.delta}
                  description="vs last period"
                />
              ))
            ) : (
              <EmptyState
                icon="dashboard"
                title="No metrics yet"
                description="KPI data will appear once your project has active deliverables."
                action={{ label: 'Configure data sources', href: '/config' }}
              />
            )}
          </div>
          {currentActivity && (
            <p className={styles.activityNote}>
              Current activity: <strong>{currentActivity.name}</strong>
            </p>
          )}
          {!isLoading && <p className={styles.statusNote} aria-live="polite">Latest metrics loaded.</p>}
          {errorMessage && <p className={styles.errorNote}>{errorMessage}</p>}
        </section>



        {type === 'portfolio' && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Methodology map</h2>
                <p className={styles.sectionSubtitle}>Portfolio governance map across intake, delivery, and value realization stages.</p>
              </div>
              <button type="button" className={styles.secondaryAction} onClick={() => navigate('/analytics/dashboard')}>
                Open portfolio dashboard
              </button>
            </div>
            <p className={styles.statusNote}>Map includes stage-gate checkpoints and portfolio-level approval controls.</p>
          </section>
        )}

        {type === 'program' && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Roadmap and dependency map</h2>
                <p className={styles.sectionSubtitle}>Program milestone sequencing with dependency and cross-team constraint visibility.</p>
              </div>
              <button type="button" className={styles.secondaryAction} onClick={() => navigate('/workflows/monitoring')}>
                Open dependency monitor
              </button>
            </div>
            <p className={styles.statusNote}>Dependency hotspots are highlighted based on recent pipeline moves and issue status.</p>
          </section>
        )}

        {type === 'project' && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Project artifacts</h2>
                <p className={styles.sectionSubtitle}>Open methodology activities to generate and review project artifacts.</p>
              </div>
              <button type="button" className={styles.secondaryAction} onClick={() => navigate(`/projects/${encodeURIComponent(entityId)}/config`)}>
                Open project configuration
              </button>
            </div>
            <p className={styles.statusNote}>Use methodology navigation to open canvases for scope, plan, risks, and approvals.</p>
          </section>
        )}

        {scenarioModelingEnabled && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Scenario comparison</h2>
                <p className={styles.sectionSubtitle}>
                  Compare baseline outcomes against schedule and financial variants.
                </p>
              </div>
              <button type="button" className={styles.secondaryAction}>
                Compare scenarios
              </button>
            </div>
            <div className={styles.scenarioGrid}>
              {scenarioSnapshots.map((scenario) => (
                <article key={scenario.id} className={styles.scenarioCard}>
                  <div className={styles.scenarioHeader}>
                    <h3 className={styles.scenarioTitle}>{scenario.label}</h3>
                    <span
                      className={`${styles.scenarioTone} ${styles[`tone${scenario.tone}`]}`}
                    >
                      {scenario.variance} variance
                    </span>
                  </div>
                  <p className={styles.scenarioSummary}>{scenario.summary}</p>
                  <div className={styles.scenarioMetrics}>
                    <div>
                      <span className={styles.metricLabel}>Schedule</span>
                      <span className={styles.metricValue}>{scenario.schedule}</span>
                    </div>
                    <div>
                      <span className={styles.metricLabel}>Budget</span>
                      <span className={styles.metricValue}>{scenario.budget}</span>
                    </div>
                    <div>
                      <span className={styles.metricLabel}>Forecast</span>
                      <span className={styles.metricValue}>{scenario.forecast}</span>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {supportsPipelineView && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Pipeline & tranche view</h2>
                <p className={styles.sectionSubtitle}>
                  Track intake requests and active projects across governance stages.
                </p>
              </div>
            </div>
            <div className={styles.pipelineFilters}>
              <input
                type="search"
                placeholder="Search by title, sponsor, or summary..."
                value={pipelineSearch}
                onChange={(event) => setPipelineSearch(event.target.value)}
                className={styles.filterInput}
              />
              <select
                className={styles.filterSelect}
                value={pipelineSponsorFilter}
                onChange={(event) => setPipelineSponsorFilter(event.target.value)}
              >
                <option value="all">All sponsors</option>
                {pipelineSponsors.map((sponsor) => (
                  <option key={sponsor} value={sponsor}>
                    {sponsor}
                  </option>
                ))}
              </select>
              <select
                className={styles.filterSelect}
                value={pipelinePriorityFilter}
                onChange={(event) => setPipelinePriorityFilter(event.target.value)}
              >
                <option value="all">All priorities</option>
                {pipelinePriorities.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>
            </div>
            {pipelineLoading && (
              <div
                className={styles.pipelineSkeletonBoard}
                aria-busy="true"
                aria-live="off"
              >
                {Array.from({ length: 4 }).map((_, columnIndex) => (
                  <div key={`pipeline-skeleton-${columnIndex}`} className={styles.pipelineSkeletonColumn}>
                    <div className={styles.pipelineSkeletonHeader}>
                      <Skeleton variant="text" width="55%" />
                      <Skeleton variant="circle" width="1.8rem" height="1.8rem" />
                    </div>
                    <Skeleton variant="card" className={styles.pipelineSkeletonCard} />
                    <Skeleton variant="card" className={styles.pipelineSkeletonCard} />
                  </div>
                ))}
              </div>
            )}
            {!pipelineLoading && <p className={styles.statusNote} aria-live="polite">Pipeline view loaded.</p>}
            <p className={styles.srOnly} aria-live="assertive" aria-atomic="true">
              {pipelineLiveMessage}
            </p>
            {pipelineError && <p className={styles.errorNote}>{pipelineError}</p>}
            {pipelineBoard ? (
              <div className={styles.pipelineBoard}>
                {pipelineBoard.stages.map((stage) => {
                  const items = pipelineItemsByStage.get(stage) ?? [];
                  const intakeItems = items.filter((item) => item.type === 'intake');
                  const projectItems = items.filter((item) => item.type === 'project');
                  return (
                    <div
                      key={stage}
                      className={`${styles.pipelineColumn} ${grabbedCurrentStage === stage ? styles.pipelineColumnTarget : ''}`}
                      role="list"
                      aria-label={`${stage} stage`}
                      aria-dropeffect={draggedItemId || grabbedItemId ? 'move' : undefined}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => handlePipelineDrop(event, stage)}
                    >
                      <div className={styles.pipelineColumnHeader}>
                        <div className={styles.pipelineStageInfo}>
                          <span>{stage}</span>
                          <span className={styles.pipelineStageMeta}>
                            {intakeItems.length} intake · {projectItems.length} projects
                          </span>
                        </div>
                        <span className={styles.pipelineStageCount}>{items.length}</span>
                      </div>
                      <div className={styles.pipelineColumnBody}>
                        <div className={styles.pipelineSection}>
                          <div className={styles.pipelineSectionHeader}>
                            Intake requests
                          </div>
                          <div className={styles.pipelineSectionBody}>
                            {intakeItems.length > 0 ? (
                              intakeItems.map(renderPipelineItem)
                            ) : (
                              <EmptyState
                                icon="timeline"
                                title="Pipeline is empty"
                                description="Add items to your pipeline to track delivery stages."
                                action={{ label: 'Add pipeline item', href: '/intake' }}
                              />
                            )}
                          </div>
                        </div>
                        <div className={styles.pipelineSection}>
                          <div className={styles.pipelineSectionHeader}>
                            Active projects
                          </div>
                          <div className={styles.pipelineSectionBody}>
                            {projectItems.length > 0 ? (
                              projectItems.map(renderPipelineItem)
                            ) : (
                              <EmptyState
                                icon="timeline"
                                title="Pipeline is empty"
                                description="Add items to your pipeline to track delivery stages."
                                action={{ label: 'Add pipeline item', href: '/intake' }}
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              !pipelineLoading && (
                <EmptyState
                  icon="timeline"
                  title="Pipeline is empty"
                  description="Add items to your pipeline to track delivery stages."
                  action={{ label: 'Add pipeline item', href: '/intake' }}
                />
              )
            )}
          </section>
        )}

        {multiAgentCollabEnabled && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Holistic insights</h2>
                <p className={styles.sectionSubtitle}>
                  Shared intelligence across agents, unified into a single decision-ready view.
                </p>
              </div>
              <button type="button" className={styles.secondaryAction}>
                Open collaboration hub
              </button>
            </div>
            <div className={styles.insightsGrid}>
              {holisticInsights.map((insight) => (
                <article key={insight.id} className={styles.insightCard}>
                  <div className={styles.insightHeader}>
                    <h3 className={styles.insightTitle}>{insight.title}</h3>
                    <span className={`${styles.insightImpact} ${styles[`impact${insight.impact}`]}`}>
                      {insight.impact} impact
                    </span>
                  </div>
                  <p className={styles.insightSummary}>{insight.summary}</p>
                  <div className={styles.insightMeta}>
                    <span>
                      Recommendation: <strong>{insight.recommendation}</strong>
                    </span>
                    <span className={styles.insightConfidence}>
                      Confidence {insight.confidence}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Demand pipeline</h2>
          <p className={styles.sectionSubtitle}>
            Visualize pipeline throughput from intake to delivery with targets and trend signals.
          </p>
          <div className={styles.pipeline}>
            {dashboardData.pipeline.length > 0 ? (
              dashboardData.pipeline.map((stage) => {
                const percentage = stage.target
                  ? Math.min(100, Math.round((stage.count / stage.target) * 100))
                  : 0;
                return (
                  <div key={stage.stage} className={styles.pipelineCard}>
                    <div className={styles.pipelineHeader}>
                      <span className={styles.pipelineStage}>{stage.stage}</span>
                      <span className={styles.pipelineCount}>
                        {stage.count}/{stage.target}
                      </span>
                    </div>
                    <div
                      className={styles.pipelineBar}
                      role="progressbar"
                      aria-valuenow={percentage}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    >
                      <span
                        className={styles.pipelineFill}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className={styles.pipelineTrend}>
                      {stage.trend === 'up' && '▲ Accelerating'}
                      {stage.trend === 'down' && '▼ Slowing'}
                      {stage.trend === 'steady' && '● Steady'}
                    </span>
                  </div>
                );
              })
            ) : (
              <EmptyState
                icon="timeline"
                title="Pipeline is empty"
                description="Add items to your pipeline to track delivery stages."
                action={{ label: 'Add pipeline item', href: '/intake' }}
              />
            )}
          </div>
        </section>

        <div className={styles.grid}>
          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Health metrics</h3>
            <div className={styles.healthGrid}>
              {dashboardData.healthMetrics.length > 0 ? (
                dashboardData.healthMetrics.map((metric) => (
                  <div key={metric.label} className={styles.healthItem}>
                    <StatusIndicator status={metric.status} />
                    <div>
                      <div className={styles.healthValue}>{metric.value}</div>
                      <div className={styles.healthLabel}>{metric.label}</div>
                    </div>
                  </div>
                ))
              ) : (
                <p className={styles.emptyState}>No health metrics reported yet.</p>
              )}
            </div>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Charters</h3>
            <ul className={styles.list}>
              {dashboardData.charters.length > 0 ? (
                dashboardData.charters.map((charter) => (
                  <li key={charter.id} className={styles.listItem}>
                    <div>
                      <div className={styles.listTitle}>{charter.name}</div>
                      <div className={styles.listMeta}>
                        Owner: {charter.owner} · Updated {charter.updated}
                      </div>
                    </div>
                    <span className={styles.badge}>{charter.status}</span>
                  </li>
                ))
              ) : (
                <li className={styles.emptyState}>No charter snapshots available.</li>
              )}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>WBS snapshot</h3>
            <ul className={styles.treeList}>
              {dashboardData.wbs.length > 0 ? (
                dashboardData.wbs.map((item) => (
                  <li key={item.name}>
                    <span className={styles.treeTitle}>{item.name}</span>
                    <ul>
                      {item.children.map((child) => (
                        <li key={child} className={styles.treeItem}>
                          {child}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))
              ) : (
                <li className={styles.emptyState}>No WBS entries available.</li>
              )}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Requirements</h3>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Title</th>
                    <th scope="col">Priority</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardData.requirements.length > 0 ? (
                    dashboardData.requirements.map((req) => (
                      <tr key={req.id}>
                        <td>{req.id}</td>
                        <td>{req.title}</td>
                        <td>{req.priority}</td>
                        <td>{req.status}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className={styles.emptyState}>
                        No requirements captured yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Risks</h3>
            <ul className={styles.list}>
              {dashboardData.risks.length > 0 ? (
                dashboardData.risks.map((risk) => (
                  <li key={risk.id} className={styles.listItem}>
                    <div>
                      <div className={styles.listTitle}>{risk.title}</div>
                      <div className={styles.listMeta}>Owner: {risk.owner}</div>
                    </div>
                    <span className={`${styles.badge} ${styles[`badge${risk.severity}`]}`}>
                      {risk.severity}
                    </span>
                  </li>
                ))
              ) : (
                <li className={styles.emptyState}>No risk summary available.</li>
              )}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>Issues</h3>
            <ul className={styles.list}>
              {dashboardData.issues.length > 0 ? (
                dashboardData.issues.map((issue) => (
                  <li key={issue.id} className={styles.listItem}>
                    <div>
                      <div className={styles.listTitle}>{issue.title}</div>
                      <div className={styles.listMeta}>Owner: {issue.owner}</div>
                    </div>
                    <span className={styles.badge}>{issue.status}</span>
                  </li>
                ))
              ) : (
                <li className={styles.emptyState}>No active issues reported.</li>
              )}
            </ul>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>{relatedLabel}</h3>
            <div className={styles.listControls}>
              <input
                type="search"
                placeholder={`Filter ${relatedLabel.toLowerCase()}...`}
                value={relatedFilter}
                onChange={(event) => setRelatedFilter(event.target.value)}
                className={styles.filterInput}
              />
              <select
                className={styles.pageSizeSelect}
                value={relatedPageSize}
                onChange={(event) => setRelatedPageSize(Number(event.target.value))}
              >
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    Show {size}
                  </option>
                ))}
              </select>
            </div>
            <ul className={styles.list}>
              {pagedRelatedItems.length > 0 ? (
                pagedRelatedItems.map((item) => (
                  <li key={item.id} className={styles.listItem}>
                    <div>
                      <div className={styles.listTitle}>{item.name}</div>
                      <div className={styles.listMeta}>
                        ID: {item.id}
                        {item.owner ? ` · Owner: ${item.owner}` : ''}
                      </div>
                    </div>
                    {item.status ? (
                      <div className={styles.statusChip}>
                        <StatusIndicator status={item.status} />
                        <span>{item.status}</span>
                      </div>
                    ) : (
                      <span className={styles.badge}>No status</span>
                    )}
                  </li>
                ))
              ) : (
                <li>
                  {dashboardData.relatedItems.length === 0 ? (
                    <EmptyState
                      icon="search"
                      title={`No ${relatedLabel.toLowerCase()}`}
                      description={`Items appear here when ${relatedLabel.toLowerCase()} are available.`}
                    />
                  ) : (
                    <EmptyState
                      icon="search"
                      title="No matches"
                      description="Try adjusting your filter criteria."
                      action={{ label: 'Clear filter', onClick: () => setRelatedFilter('') }}
                    />
                  )}
                </li>
              )}
            </ul>
            {filteredRelatedItems.length > relatedPageSize && (
              <div className={styles.pagination}>
                <button
                  type="button"
                  onClick={() => setRelatedPage((page) => Math.max(1, page - 1))}
                  className={styles.pageButton}
                  disabled={relatedPage <= 1}
                >
                  Previous
                </button>
                <span className={styles.pageInfo}>
                  Page {relatedPage} of {relatedTotalPages}
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setRelatedPage((page) => Math.min(relatedTotalPages, page + 1))
                  }
                  className={styles.pageButton}
                  disabled={relatedPage >= relatedTotalPages}
                >
                  Next
                </button>
              </div>
            )}
          </section>
        </div>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Stakeholder notification settings</h2>
              <p className={styles.sectionSubtitle}>
                Configure notification cadence and channels for sponsors, delivery leads, and
                governance stakeholders.
              </p>
            </div>
            <button type="button" className={styles.secondaryAction}>
              Save preferences
            </button>
          </div>
          <div className={styles.notificationGrid}>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Update cadence</h3>
              <label className={styles.fieldLabel} htmlFor="cadence">
                Summary frequency
              </label>
              <select id="cadence" className={styles.fieldSelect} defaultValue="weekly">
                <option value="daily">Daily digest</option>
                <option value="weekly">Weekly summary</option>
                <option value="monthly">Monthly portfolio review</option>
              </select>
              <label className={styles.fieldLabel} htmlFor="timezone">
                Delivery timezone
              </label>
              <select id="timezone" className={styles.fieldSelect} defaultValue="utc">
                <option value="utc">UTC</option>
                <option value="pst">Pacific (PST)</option>
                <option value="cet">Central Europe (CET)</option>
              </select>
            </div>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Notification channels</h3>
              <div className={styles.checkboxGroup}>
                <label>
                  <input type="checkbox" defaultChecked /> Email summaries
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Slack/Teams alerts
                </label>
                <label>
                  <input type="checkbox" /> Executive PDF pack
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Risk escalation alerts
                </label>
              </div>
            </div>
            <div className={styles.notificationCard}>
              <h3 className={styles.cardSubtitle}>Stakeholder segments</h3>
              <div className={styles.checkboxGroup}>
                <label>
                  <input type="checkbox" defaultChecked /> Sponsors
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Delivery leadership
                </label>
                <label>
                  <input type="checkbox" defaultChecked /> Governance board
                </label>
                <label>
                  <input type="checkbox" /> Vendor partners
                </label>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default WorkspacePage;
