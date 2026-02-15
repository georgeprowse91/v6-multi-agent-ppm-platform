import { useEffect, useMemo, useState } from 'react';

type DemandItem = { id: string; title: string; status: string; value?: number; effort?: number; risk?: number; score?: number };
type Scenario = { id: string; name: string; value_score: number; budget: number; published?: boolean };

export default function EnterpriseUpliftPage() {
  const portfolioId = 'demo-portfolio';
  const [view, setView] = useState<'table' | 'kanban'>('table');
  const [demand, setDemand] = useState<DemandItem[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('');

  const load = async () => {
    const [demandRes, scoreRes, scenarioRes] = await Promise.all([
      fetch(`/v1/api/portfolio/${portfolioId}/demand`),
      fetch(`/v1/api/portfolio/${portfolioId}/prioritisation/score`, { method: 'POST' }),
      fetch(`/v1/api/portfolio/${portfolioId}/scenarios/compare`),
    ]);
    const demandBody = await demandRes.json();
    const scoreBody = await scoreRes.json();
    const scenarioBody = await scenarioRes.json();
    const scores = new Map((scoreBody.results ?? []).map((item: DemandItem) => [item.id, item.score]));
    setDemand((demandBody.items ?? []).map((item: DemandItem) => ({ ...item, score: scores.get(item.id) })));
    setScenarios(scenarioBody.scenarios ?? []);
  };

  useEffect(() => {
    void load();
  }, []);

  const grouped = useMemo(() => demand.reduce<Record<string, DemandItem[]>>((acc, item) => {
    const key = item.status ?? 'unknown';
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {}), [demand]);

  const publishDecision = async () => {
    if (!selectedScenario) return;
    await fetch(`/v1/api/portfolio/${portfolioId}/scenarios/${selectedScenario}/publish`, { method: 'POST' });
    await load();
  };

  return (
    <div style={{ padding: 16 }}>
      <h1>Enterprise Portfolio Workspace</h1>
      <button onClick={() => setView(view === 'table' ? 'kanban' : 'table')} type="button">
        Toggle {view === 'table' ? 'Kanban' : 'Table'}
      </button>
      {view === 'table' ? (
        <table aria-label="Demand board table">
          <thead><tr><th>Title</th><th>Status</th><th>Score</th></tr></thead>
          <tbody>
            {demand.map((item) => <tr key={item.id}><td>{item.title}</td><td>{item.status}</td><td>{item.score ?? '-'}</td></tr>)}
          </tbody>
        </table>
      ) : (
        <div aria-label="Demand board kanban" style={{ display: 'flex', gap: 12 }}>
          {Object.entries(grouped).map(([status, items]) => (
            <section key={status}><h3>{status}</h3>{items.map((item) => <div key={item.id}>{item.title}</div>)}</section>
          ))}
        </div>
      )}

      <h2>Scenario Compare</h2>
      <div aria-label="Scenario compare">
        {scenarios.map((scenario) => (
          <label key={scenario.id} style={{ display: 'block' }}>
            <input type="radio" name="scenario" value={scenario.id} checked={selectedScenario === scenario.id} onChange={(e) => setSelectedScenario(e.target.value)} />
            {scenario.name} · value {scenario.value_score} · budget {scenario.budget} {scenario.published ? '(published)' : ''}
          </label>
        ))}
      </div>
      <button type="button" onClick={publishDecision}>Publish decision</button>
    </div>
  );
}
