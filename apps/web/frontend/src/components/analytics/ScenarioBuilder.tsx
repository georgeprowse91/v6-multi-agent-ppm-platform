import { useCallback, useEffect, useState } from 'react';
import styles from './ScenarioBuilder.module.css';

interface ScenarioTemplate {
  template_id: string;
  name: string;
  description: string;
  domain: string;
  parameters: Record<string, unknown>;
}

interface ScenarioComparison {
  budget_variance: number;
  budget_variance_pct: number;
  eac_variance: number;
  schedule_variance_days: number;
  cpi_delta: number;
  spi_delta: number;
}

interface CascadeImpact {
  project_id: string;
  propagation_weight: number;
  original_budget: number;
  cascaded_budget_delta: number;
  cascaded_schedule_delta_days: number;
  adjusted_eac: number;
  risk_indicator: string;
}

interface ScenarioResult {
  scenario_id: string;
  name: string;
  template_id: string | null;
  entity_id: string;
  entity_type: string;
  parameters: Record<string, unknown>;
  baseline: Record<string, number>;
  scenario: Record<string, number>;
  comparison: ScenarioComparison;
  cascade_impacts?: {
    source_project_id: string;
    total_linked_projects: number;
    total_cascaded_budget_impact: number;
    impacts: CascadeImpact[];
  };
  generated_at: string;
}

interface ScenarioBuilderProps {
  projectId: string;
  portfolioId?: string;
}

const formatCurrency = (value: number): string => {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

const formatDelta = (value: number, suffix = ''): string => {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}${suffix}`;
};

const deltaClass = (value: number, invert = false): string => {
  if (value === 0) return styles.neutral;
  const isPositive = invert ? value < 0 : value > 0;
  return isPositive ? styles.positive : styles.negative;
};

export function ScenarioBuilder({ projectId, portfolioId }: ScenarioBuilderProps) {
  const [templates, setTemplates] = useState<ScenarioTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [budgetMultiplier, setBudgetMultiplier] = useState(1.0);
  const [costMultiplier, setCostMultiplier] = useState(1.0);
  const [durationMultiplier, setDurationMultiplier] = useState(1.0);
  const [scenarioName, setScenarioName] = useState('');
  const [linkedProjectIds, setLinkedProjectIds] = useState<string[]>([]);
  const [linkedInput, setLinkedInput] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/v1/api/scenarios/templates')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: { templates: ScenarioTemplate[] }) => setTemplates(data.templates))
      .catch(() => setTemplates([]));
  }, []);

  const selectTemplate = useCallback(
    (templateId: string) => {
      if (selectedTemplate === templateId) {
        setSelectedTemplate(null);
        setBudgetMultiplier(1.0);
        setCostMultiplier(1.0);
        setDurationMultiplier(1.0);
        setScenarioName('');
        return;
      }
      setSelectedTemplate(templateId);
      const tmpl = templates.find((t) => t.template_id === templateId);
      if (tmpl) {
        const params = tmpl.parameters;
        setBudgetMultiplier(Number(params.budget_multiplier ?? 1.0));
        setCostMultiplier(Number(params.cost_multiplier ?? 1.0));
        setDurationMultiplier(Number(params.duration_multiplier ?? 1.0));
        setScenarioName(tmpl.name);
      }
    },
    [selectedTemplate, templates]
  );

  const addLinkedProject = useCallback(() => {
    const trimmed = linkedInput.trim();
    if (trimmed && !linkedProjectIds.includes(trimmed)) {
      setLinkedProjectIds((prev) => [...prev, trimmed]);
    }
    setLinkedInput('');
  }, [linkedInput, linkedProjectIds]);

  const removeLinkedProject = useCallback((id: string) => {
    setLinkedProjectIds((prev) => prev.filter((p) => p !== id));
  }, []);

  const resetForm = useCallback(() => {
    setSelectedTemplate(null);
    setBudgetMultiplier(1.0);
    setCostMultiplier(1.0);
    setDurationMultiplier(1.0);
    setScenarioName('');
    setLinkedProjectIds([]);
    setLinkedInput('');
    setResult(null);
    setError(null);
  }, []);

  const runScenario = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const body: Record<string, unknown> = {
        parameters: {
          budget_multiplier: budgetMultiplier,
          cost_multiplier: costMultiplier,
          duration_multiplier: durationMultiplier,
        },
      };

      if (projectId) body.project_id = projectId;
      if (portfolioId) body.portfolio_id = portfolioId;
      if (selectedTemplate) body.template_id = selectedTemplate;
      if (scenarioName) body.name = scenarioName;
      if (linkedProjectIds.length > 0) body.linked_project_ids = linkedProjectIds;

      const response = await fetch('/v1/api/scenarios/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(
          (detail as Record<string, string>).detail ?? `Request failed (${response.status})`
        );
      }

      const data: ScenarioResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run scenario');
    } finally {
      setRunning(false);
    }
  }, [
    budgetMultiplier,
    costMultiplier,
    durationMultiplier,
    linkedProjectIds,
    portfolioId,
    projectId,
    scenarioName,
    selectedTemplate,
  ]);

  return (
    <div className={styles.container}>
      {/* Template selection */}
      <div>
        <div className={styles.sectionTitle}>Scenario Templates</div>
        <div className={styles.templateGrid}>
          {templates.map((tmpl) => (
            <button
              key={tmpl.template_id}
              type="button"
              className={`${styles.templateCard} ${
                selectedTemplate === tmpl.template_id ? styles.templateCardSelected : ''
              }`}
              onClick={() => selectTemplate(tmpl.template_id)}
            >
              <div className={styles.templateName}>{tmpl.name}</div>
              <div className={styles.templateDesc}>{tmpl.description}</div>
              <span className={styles.templateDomain}>{tmpl.domain}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Custom parameter sliders */}
      <div className={styles.customSection}>
        <div className={styles.sectionTitle}>Adjust Parameters</div>

        <div className={styles.sliderGroup}>
          <label className={styles.sliderLabel}>
            <span>Scenario Name</span>
          </label>
          <input
            type="text"
            value={scenarioName}
            onChange={(e) => setScenarioName(e.target.value)}
            placeholder="Custom Scenario"
            style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #d0d4dd', fontSize: '13px' }}
          />
        </div>

        <div className={styles.sliderGroup}>
          <label className={styles.sliderLabel}>
            <span>Budget Multiplier</span>
            <span className={styles.sliderValue}>{(budgetMultiplier * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            className={styles.slider}
            min="0.5"
            max="2.0"
            step="0.05"
            value={budgetMultiplier}
            onChange={(e) => setBudgetMultiplier(Number(e.target.value))}
          />
        </div>

        <div className={styles.sliderGroup}>
          <label className={styles.sliderLabel}>
            <span>Cost Multiplier</span>
            <span className={styles.sliderValue}>{(costMultiplier * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            className={styles.slider}
            min="0.5"
            max="2.0"
            step="0.05"
            value={costMultiplier}
            onChange={(e) => setCostMultiplier(Number(e.target.value))}
          />
        </div>

        <div className={styles.sliderGroup}>
          <label className={styles.sliderLabel}>
            <span>Duration Multiplier</span>
            <span className={styles.sliderValue}>{(durationMultiplier * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            className={styles.slider}
            min="0.5"
            max="2.0"
            step="0.05"
            value={durationMultiplier}
            onChange={(e) => setDurationMultiplier(Number(e.target.value))}
          />
        </div>

        {/* Linked projects for cascade analysis */}
        <div className={styles.sliderGroup}>
          <label className={styles.sliderLabel}>
            <span>Linked Projects (cascade impact)</span>
          </label>
          <div className={styles.linkedInput}>
            <input
              type="text"
              value={linkedInput}
              onChange={(e) => setLinkedInput(e.target.value)}
              placeholder="Enter project ID"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addLinkedProject();
                }
              }}
            />
            <button type="button" onClick={addLinkedProject}>
              Add
            </button>
          </div>
          {linkedProjectIds.length > 0 && (
            <div className={styles.linkedTags}>
              {linkedProjectIds.map((id) => (
                <span key={id} className={styles.linkedTag}>
                  {id}
                  <button type="button" onClick={() => removeLinkedProject(id)}>
                    x
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.runButton}
          onClick={runScenario}
          disabled={running}
        >
          {running ? 'Running...' : 'Run Scenario'}
        </button>
        <button type="button" className={styles.resetButton} onClick={resetForm}>
          Reset
        </button>
      </div>

      {error && <div className={styles.errorMessage}>{error}</div>}

      {/* Results */}
      {result && (
        <div className={styles.resultPanel}>
          <div className={styles.resultTitle}>
            {result.name}
            <span className={styles.savedBadge}>Saved</span>
          </div>

          <div className={styles.comparisonGrid}>
            <div className={styles.comparisonCard}>
              <span className={styles.comparisonLabel}>Budget</span>
              <span className={styles.comparisonBaseline}>
                Baseline: {formatCurrency(result.baseline.budget ?? 0)}
              </span>
              <span className={styles.comparisonScenario}>
                {formatCurrency(result.scenario.budget ?? 0)}
              </span>
              <span className={deltaClass(result.comparison.budget_variance, true)}>
                {formatDelta(result.comparison.budget_variance_pct, '%')}
              </span>
            </div>

            <div className={styles.comparisonCard}>
              <span className={styles.comparisonLabel}>Forecast EAC</span>
              <span className={styles.comparisonBaseline}>
                Baseline: {formatCurrency(result.baseline.forecast_eac ?? 0)}
              </span>
              <span className={styles.comparisonScenario}>
                {formatCurrency(result.scenario.forecast_eac ?? 0)}
              </span>
              <span className={deltaClass(result.comparison.eac_variance, true)}>
                {formatDelta(result.comparison.eac_variance)}
              </span>
            </div>

            <div className={styles.comparisonCard}>
              <span className={styles.comparisonLabel}>Schedule</span>
              <span className={styles.comparisonBaseline}>
                Baseline: {result.baseline.schedule_days ?? 0} days
              </span>
              <span className={styles.comparisonScenario}>
                {result.scenario.schedule_days ?? 0} days
              </span>
              <span className={deltaClass(result.comparison.schedule_variance_days, true)}>
                {formatDelta(result.comparison.schedule_variance_days, ' days')}
              </span>
            </div>

            <div className={styles.comparisonCard}>
              <span className={styles.comparisonLabel}>CPI / SPI</span>
              <span className={styles.comparisonBaseline}>
                CPI: {(result.baseline.cost_performance_index ?? 1).toFixed(2)} | SPI:{' '}
                {(result.baseline.schedule_performance_index ?? 1).toFixed(2)}
              </span>
              <span className={styles.comparisonScenario}>
                CPI: {(result.scenario.cost_performance_index ?? 1).toFixed(2)} | SPI:{' '}
                {(result.scenario.schedule_performance_index ?? 1).toFixed(2)}
              </span>
              <span className={deltaClass(result.comparison.cpi_delta)}>
                CPI {formatDelta(result.comparison.cpi_delta)} | SPI{' '}
                {formatDelta(result.comparison.spi_delta)}
              </span>
            </div>
          </div>

          {/* Cascade impacts */}
          {result.cascade_impacts && result.cascade_impacts.impacts.length > 0 && (
            <div className={styles.cascadeSection}>
              <div className={styles.cascadeTitle}>
                Cascade Impact ({result.cascade_impacts.total_linked_projects} linked projects |
                Total: {formatCurrency(result.cascade_impacts.total_cascaded_budget_impact)})
              </div>
              <table className={styles.cascadeTable}>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Weight</th>
                    <th>Budget Impact</th>
                    <th>Schedule Impact</th>
                    <th>Adjusted EAC</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {result.cascade_impacts.impacts.map((impact) => (
                    <tr key={impact.project_id}>
                      <td>{impact.project_id}</td>
                      <td>{(impact.propagation_weight * 100).toFixed(0)}%</td>
                      <td>{formatCurrency(impact.cascaded_budget_delta)}</td>
                      <td>{formatDelta(impact.cascaded_schedule_delta_days, ' days')}</td>
                      <td>{formatCurrency(impact.adjusted_eac)}</td>
                      <td
                        className={
                          impact.risk_indicator === 'high' ? styles.riskHigh : styles.riskLow
                        }
                      >
                        {impact.risk_indicator}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ScenarioBuilder;
