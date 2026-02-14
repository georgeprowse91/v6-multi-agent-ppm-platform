import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './WorkspaceDirectoryPage.module.css';

type WorkspaceType = 'portfolio' | 'program' | 'project';

interface WorkspaceDirectoryPageProps {
  type: WorkspaceType;
}

interface WorkspaceRecord {
  id: string;
  name: string;
  owner: string;
  status: string;
  summary: string;
}

const seededRecords: Record<WorkspaceType, WorkspaceRecord[]> = {
  portfolio: [
    { id: 'demo', name: 'Enterprise Transformation Portfolio', owner: 'PMO Office', status: 'On track', summary: 'Tracks strategic modernization investments and stage-gate health.' },
    { id: 'cloud', name: 'Cloud Migration Portfolio', owner: 'Platform Office', status: 'Needs attention', summary: 'Coordinates multi-program migration readiness and risk posture.' },
  ],
  program: [
    { id: 'demo', name: 'Customer Experience Program', owner: 'Jane Alvarez', status: 'On track', summary: 'Aligns onboarding, support, and retention initiatives.' },
    { id: 'supply-chain', name: 'Supply Chain Optimization', owner: 'Marco Singh', status: 'At risk', summary: 'Improves demand sensing and partner integration milestones.' },
  ],
  project: [
    { id: 'demo', name: 'Digital Onboarding Revamp', owner: 'Maya Chen', status: 'Executing', summary: 'Delivers a guided onboarding journey and workflow automation.' },
    { id: 'erp-uplift', name: 'ERP Reporting Uplift', owner: 'Liam Patel', status: 'Planning', summary: 'Introduces unified reporting packs and governance controls.' },
  ],
};

const labels: Record<WorkspaceType, string> = {
  portfolio: 'Portfolio',
  program: 'Program',
  project: 'Project',
};

export function WorkspaceDirectoryPage({ type }: WorkspaceDirectoryPageProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [records, setRecords] = useState<WorkspaceRecord[]>(seededRecords[type]);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadRecords = async () => {
      try {
        const response = await fetch(`/api/${type}s`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error('Unable to load records');
        }
        const payload = await response.json();
        const normalized = Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload)
            ? payload
            : [];
        if (!isMounted || normalized.length === 0) return;
        setRecords(
          normalized.map((item: Record<string, string>) => ({
            id: String(item.id ?? item[`${type}_id`] ?? item.slug ?? ''),
            name: String(item.name ?? `${labels[type]} ${item.id ?? ''}`),
            owner: String(item.owner ?? item.sponsor ?? 'Unassigned'),
            status: String(item.status ?? 'Unknown'),
            summary: String(item.summary ?? item.description ?? 'No summary provided yet.'),
          })).filter((item: WorkspaceRecord) => item.id)
        );
      } catch {
        // fallback to seeded records for offline/demo environments
      }
    };

    void loadRecords();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [type]);

  const filteredRecords = useMemo(() => {
    const lowered = search.trim().toLowerCase();
    if (!lowered) return records;
    return records.filter((record) =>
      `${record.id} ${record.name} ${record.owner} ${record.status}`.toLowerCase().includes(lowered)
    );
  }, [records, search]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Open {labels[type]} workspace</h1>
        <p>Search and open an existing {type} workspace.</p>
      </header>
      <label className={styles.searchLabel} htmlFor={`${type}-search`}>
        Search {labels[type]}s
      </label>
      <input
        id={`${type}-search`}
        type="search"
        className={styles.searchInput}
        placeholder={`Search by ${type} ID, name, or owner`}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <ul className={styles.list}>
        {filteredRecords.map((record) => (
          <li key={record.id} className={styles.card}>
            <div>
              <h2>{record.name}</h2>
              <p className={styles.meta}>{record.id} · {record.owner} · {record.status}</p>
              <p>{record.summary}</p>
            </div>
            <button
              type="button"
              className={styles.openButton}
              onClick={() => navigate(`/${type}s/${encodeURIComponent(record.id)}`)}
            >
              Open workspace
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default WorkspaceDirectoryPage;
