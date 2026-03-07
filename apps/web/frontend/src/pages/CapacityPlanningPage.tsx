import { useCallback, useEffect, useState } from 'react';
import styles from './CapacityPlanningPage.module.css';

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface SkillGap {
  skill: string;
  demand_headcount: number;
  supply_count: number;
  headcount_gap: number;
  demand_hours: number;
  supply_hours: number;
  hours_gap: number;
  avg_supply_proficiency: number;
  min_required_proficiency: number;
  project_count: number;
  severity: string;
}

interface RoleGap {
  role: string;
  demand_headcount: number;
  supply_count: number;
  headcount_gap: number;
  project_count: number;
}

interface SkillEntry {
  skill: string;
  total_headcount?: number;
  total_hours?: number;
  available_count?: number;
  available_hours?: number;
  avg_proficiency?: number;
  project_count?: number;
}

interface Recommendation {
  type: string;
  skill: string;
  count: number;
  priority: string;
  rationale: string;
}

interface DemandSummary {
  total_demand_hours: number;
  total_supply_hours: number;
  capacity_ratio: number;
  unique_skills_demanded: number;
  unique_roles_demanded: number;
  total_skill_gaps: number;
  total_role_gaps: number;
  critical_gaps: number;
}

interface PortfolioDemandData {
  portfolio_id: string;
  summary: DemandSummary;
  demand_by_skill: SkillEntry[];
  supply_by_skill: SkillEntry[];
  demand_by_role: SkillEntry[];
  supply_by_role: SkillEntry[];
  skill_gaps: SkillGap[];
  role_gaps: RoleGap[];
  recommendations: Recommendation[];
}

/* ------------------------------------------------------------------ */
/* Demo data (used when API is unavailable)                            */
/* ------------------------------------------------------------------ */

const DEMO_DATA: PortfolioDemandData = {
  portfolio_id: 'default',
  summary: {
    total_demand_hours: 12400,
    total_supply_hours: 9800,
    capacity_ratio: 0.79,
    unique_skills_demanded: 18,
    unique_roles_demanded: 8,
    total_skill_gaps: 6,
    total_role_gaps: 3,
    critical_gaps: 2,
  },
  demand_by_skill: [
    { skill: 'Cloud Architecture', total_headcount: 5, total_hours: 2000, project_count: 4 },
    { skill: 'ML Engineering', total_headcount: 4, total_hours: 1600, project_count: 3 },
    { skill: 'React', total_headcount: 6, total_hours: 2400, project_count: 5 },
    { skill: 'Python', total_headcount: 8, total_hours: 3200, project_count: 7 },
    { skill: 'Security', total_headcount: 3, total_hours: 1200, project_count: 3 },
    { skill: 'DevOps', total_headcount: 4, total_hours: 1600, project_count: 4 },
    { skill: 'Data Engineering', total_headcount: 3, total_hours: 1200, project_count: 2 },
    { skill: 'Project Management', total_headcount: 4, total_hours: 1600, project_count: 4 },
  ],
  supply_by_skill: [
    { skill: 'Cloud Architecture', available_count: 2, available_hours: 800, avg_proficiency: 3.5 },
    { skill: 'ML Engineering', available_count: 1, available_hours: 400, avg_proficiency: 4.0 },
    { skill: 'React', available_count: 5, available_hours: 2000, avg_proficiency: 3.2 },
    { skill: 'Python', available_count: 7, available_hours: 2800, avg_proficiency: 3.8 },
    { skill: 'Security', available_count: 1, available_hours: 400, avg_proficiency: 4.5 },
    { skill: 'DevOps', available_count: 3, available_hours: 1200, avg_proficiency: 3.0 },
    { skill: 'Data Engineering', available_count: 2, available_hours: 800, avg_proficiency: 3.0 },
    { skill: 'Project Management', available_count: 4, available_hours: 1600, avg_proficiency: 4.0 },
  ],
  demand_by_role: [],
  supply_by_role: [],
  skill_gaps: [
    { skill: 'Cloud Architecture', demand_headcount: 5, supply_count: 2, headcount_gap: 3, demand_hours: 2000, supply_hours: 800, hours_gap: 1200, avg_supply_proficiency: 3.5, min_required_proficiency: 4, project_count: 4, severity: 'critical' },
    { skill: 'ML Engineering', demand_headcount: 4, supply_count: 1, headcount_gap: 3, demand_hours: 1600, supply_hours: 400, hours_gap: 1200, avg_supply_proficiency: 4.0, min_required_proficiency: 3, project_count: 3, severity: 'critical' },
    { skill: 'Security', demand_headcount: 3, supply_count: 1, headcount_gap: 2, demand_hours: 1200, supply_hours: 400, hours_gap: 800, avg_supply_proficiency: 4.5, min_required_proficiency: 4, project_count: 3, severity: 'high' },
    { skill: 'React', demand_headcount: 6, supply_count: 5, headcount_gap: 1, demand_hours: 2400, supply_hours: 2000, hours_gap: 400, avg_supply_proficiency: 3.2, min_required_proficiency: 3, project_count: 5, severity: 'medium' },
    { skill: 'DevOps', demand_headcount: 4, supply_count: 3, headcount_gap: 1, demand_hours: 1600, supply_hours: 1200, hours_gap: 400, avg_supply_proficiency: 3.0, min_required_proficiency: 3, project_count: 4, severity: 'medium' },
    { skill: 'Python', demand_headcount: 8, supply_count: 7, headcount_gap: 1, demand_hours: 3200, supply_hours: 2800, hours_gap: 400, avg_supply_proficiency: 3.8, min_required_proficiency: 3, project_count: 7, severity: 'medium' },
  ],
  role_gaps: [
    { role: 'Cloud Architect', demand_headcount: 3, supply_count: 1, headcount_gap: 2, project_count: 3 },
    { role: 'ML Engineer', demand_headcount: 3, supply_count: 1, headcount_gap: 2, project_count: 2 },
    { role: 'Security Engineer', demand_headcount: 2, supply_count: 1, headcount_gap: 1, project_count: 2 },
  ],
  recommendations: [
    { type: 'hire', skill: 'Cloud Architecture', count: 3, priority: 'high', rationale: '4 projects need Cloud Architecture' },
    { type: 'hire', skill: 'ML Engineering', count: 3, priority: 'high', rationale: '3 projects need ML Engineering' },
    { type: 'train', skill: 'Security', count: 2, priority: 'medium', rationale: 'Cross-train existing resources in Security' },
    { type: 'train', skill: 'React', count: 1, priority: 'medium', rationale: 'Cross-train existing resources in React' },
  ],
};

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'var(--color-danger, #ef4444)';
    case 'high': return 'var(--color-warning, #f59e0b)';
    case 'medium': return 'var(--color-info, #3b82f6)';
    default: return 'var(--color-text-tertiary, #999)';
  }
}

function priorityBadge(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

function pct(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function barWidth(demand: number, supply: number): { demandPct: string; supplyPct: string } {
  const max = Math.max(demand, supply, 1);
  return {
    demandPct: `${(demand / max) * 100}%`,
    supplyPct: `${(supply / max) * 100}%`,
  };
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function CapacityPlanningPage() {
  const [data, setData] = useState<PortfolioDemandData>(DEMO_DATA);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'skills' | 'gaps' | 'recommendations'>('overview');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch('/api/capacity/portfolio-demand?portfolio_id=default');
      if (resp.ok) {
        setData(await resp.json());
      }
    } catch {
      // Use demo data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const { summary } = data;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Capacity Planning</h1>
          <p className={styles.subtitle}>Portfolio-level supply vs demand analysis with skill gap identification</p>
        </div>
        <button className={styles.refreshBtn} onClick={loadData} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </header>

      {/* KPI Cards */}
      <div className={styles.kpiRow}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Capacity Ratio</div>
          <div className={styles.kpiValue} style={{ color: summary.capacity_ratio < 0.85 ? 'var(--color-danger, #ef4444)' : 'var(--color-success, #22c55e)' }}>
            {pct(summary.capacity_ratio)}
          </div>
          <div className={styles.kpiSub}>Supply / Demand</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Demand Hours</div>
          <div className={styles.kpiValue}>{summary.total_demand_hours.toLocaleString()}</div>
          <div className={styles.kpiSub}>{summary.unique_skills_demanded} skills across {summary.unique_roles_demanded} roles</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Supply Hours</div>
          <div className={styles.kpiValue}>{summary.total_supply_hours.toLocaleString()}</div>
          <div className={styles.kpiSub}>Available capacity</div>
        </div>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Skill Gaps</div>
          <div className={styles.kpiValue} style={{ color: summary.critical_gaps > 0 ? 'var(--color-danger, #ef4444)' : undefined }}>
            {summary.total_skill_gaps}
          </div>
          <div className={styles.kpiSub}>{summary.critical_gaps} critical</div>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        {(['overview', 'skills', 'gaps', 'recommendations'] as const).map(tab => (
          <button
            key={tab}
            className={`${styles.tab} ${activeTab === tab ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className={styles.tabContent}>
        {activeTab === 'overview' && (
          <div className={styles.overviewGrid}>
            {/* Supply vs Demand Chart */}
            <div className={styles.chartCard}>
              <h3>Supply vs Demand by Skill</h3>
              <div className={styles.barChart}>
                {data.demand_by_skill.map(d => {
                  const supply = data.supply_by_skill.find(s => s.skill === d.skill);
                  const supplyHours = supply?.available_hours ?? 0;
                  const demandHours = d.total_hours ?? 0;
                  const { demandPct, supplyPct } = barWidth(demandHours, supplyHours);
                  return (
                    <div key={d.skill} className={styles.barGroup}>
                      <div className={styles.barLabel}>{d.skill}</div>
                      <div className={styles.barContainer}>
                        <div className={styles.barDemand} style={{ width: demandPct }} title={`Demand: ${demandHours}h`} />
                        <div className={styles.barSupply} style={{ width: supplyPct }} title={`Supply: ${supplyHours}h`} />
                      </div>
                      <div className={styles.barValues}>
                        <span className={styles.demandLabel}>{demandHours}h</span>
                        <span className={styles.supplyLabel}>{supplyHours}h</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className={styles.legend}>
                <span className={styles.legendDemand}>Demand</span>
                <span className={styles.legendSupply}>Supply</span>
              </div>
            </div>

            {/* Top Gaps */}
            <div className={styles.chartCard}>
              <h3>Top Skill Gaps</h3>
              {data.skill_gaps.slice(0, 5).map(gap => (
                <div key={gap.skill} className={styles.gapRow}>
                  <div className={styles.gapHeader}>
                    <span className={styles.gapSkill}>{gap.skill}</span>
                    <span className={styles.severityBadge} style={{ background: severityColor(gap.severity) }}>
                      {gap.severity}
                    </span>
                  </div>
                  <div className={styles.gapMeta}>
                    Gap: {gap.headcount_gap} headcount | {gap.hours_gap.toLocaleString()}h | {gap.project_count} projects
                  </div>
                  <div className={styles.gapBar}>
                    <div className={styles.gapBarFill} style={{ width: `${Math.min(100, (gap.headcount_gap / gap.demand_headcount) * 100)}%`, background: severityColor(gap.severity) }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'skills' && (
          <div className={styles.tableCard}>
            <h3>Skill Supply & Demand Detail</h3>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Demand (HC)</th>
                  <th>Supply (HC)</th>
                  <th>Gap</th>
                  <th>Demand (Hours)</th>
                  <th>Supply (Hours)</th>
                  <th>Avg Proficiency</th>
                  <th>Projects</th>
                </tr>
              </thead>
              <tbody>
                {data.demand_by_skill.map(d => {
                  const supply = data.supply_by_skill.find(s => s.skill === d.skill);
                  const gap = (d.total_headcount ?? 0) - (supply?.available_count ?? 0);
                  return (
                    <tr key={d.skill}>
                      <td className={styles.skillName}>{d.skill}</td>
                      <td>{d.total_headcount ?? 0}</td>
                      <td>{supply?.available_count ?? 0}</td>
                      <td style={{ color: gap > 0 ? 'var(--color-danger, #ef4444)' : 'var(--color-success, #22c55e)', fontWeight: 600 }}>
                        {gap > 0 ? `+${gap}` : gap}
                      </td>
                      <td>{(d.total_hours ?? 0).toLocaleString()}</td>
                      <td>{(supply?.available_hours ?? 0).toLocaleString()}</td>
                      <td>{supply?.avg_proficiency?.toFixed(1) ?? '-'}</td>
                      <td>{d.project_count ?? 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'gaps' && (
          <div className={styles.gapsGrid}>
            <div className={styles.tableCard}>
              <h3>Skill Gaps</h3>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Skill</th>
                    <th>Severity</th>
                    <th>HC Gap</th>
                    <th>Hours Gap</th>
                    <th>Supply Prof.</th>
                    <th>Required Prof.</th>
                    <th>Projects</th>
                  </tr>
                </thead>
                <tbody>
                  {data.skill_gaps.map(gap => (
                    <tr key={gap.skill}>
                      <td className={styles.skillName}>{gap.skill}</td>
                      <td>
                        <span className={styles.severityBadge} style={{ background: severityColor(gap.severity) }}>
                          {gap.severity}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{gap.headcount_gap}</td>
                      <td>{gap.hours_gap.toLocaleString()}</td>
                      <td>{gap.avg_supply_proficiency.toFixed(1)}</td>
                      <td>{gap.min_required_proficiency}</td>
                      <td>{gap.project_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.role_gaps.length > 0 && (
              <div className={styles.tableCard}>
                <h3>Role Gaps</h3>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Role</th>
                      <th>Demand (HC)</th>
                      <th>Supply (HC)</th>
                      <th>Gap</th>
                      <th>Projects</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.role_gaps.map(gap => (
                      <tr key={gap.role}>
                        <td className={styles.skillName}>{gap.role}</td>
                        <td>{gap.demand_headcount}</td>
                        <td>{gap.supply_count}</td>
                        <td style={{ fontWeight: 600, color: 'var(--color-danger, #ef4444)' }}>{gap.headcount_gap}</td>
                        <td>{gap.project_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className={styles.recGrid}>
            {data.recommendations.map((rec, i) => (
              <div key={i} className={styles.recCard}>
                <div className={styles.recHeader}>
                  <span className={styles.recType}>{rec.type === 'hire' ? 'Hire' : rec.type === 'train' ? 'Train' : rec.type}</span>
                  <span className={styles.recPriority} style={{ color: rec.priority === 'high' ? 'var(--color-danger, #ef4444)' : 'var(--color-warning, #f59e0b)' }}>
                    {priorityBadge(rec.priority)}
                  </span>
                </div>
                <div className={styles.recSkill}>{rec.skill}</div>
                <div className={styles.recCount}>{rec.count} {rec.type === 'hire' ? 'positions' : 'resources'}</div>
                <div className={styles.recRationale}>{rec.rationale}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
