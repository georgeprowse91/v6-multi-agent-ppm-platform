import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestJson } from '../services/apiClient';
import { FacetedFilter, type Facet } from '../components/collections/FacetedFilter';
import { EntityTable, type ColumnDef, type EntityRecord } from '../components/collections/EntityTable';
import { BulkActions, type BulkAction } from '../components/collections/BulkActions';
import styles from './WorkspaceDirectoryPage.module.css';

type WorkspaceType = 'portfolio' | 'program' | 'project';

interface WorkspaceDirectoryPageProps {
  type: WorkspaceType;
}

const labels: Record<WorkspaceType, string> = {
  portfolio: 'Portfolio',
  program: 'Program',
  project: 'Project',
};

const pluralLabels: Record<WorkspaceType, string> = {
  portfolio: 'portfolios',
  program: 'programs',
  project: 'projects',
};

/** Column definitions per workspace type. */
const columnsByType: Record<WorkspaceType, ColumnDef[]> = {
  portfolio: [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'owner', label: 'Owner', sortable: true },
    { key: 'status', label: 'Status', sortable: true, isStatus: true },
    { key: 'classification', label: 'Classification', sortable: true },
    { key: 'updated_at', label: 'Updated', sortable: true, width: '120px' },
  ],
  program: [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'owner', label: 'Owner', sortable: true },
    { key: 'status', label: 'Status', sortable: true, isStatus: true },
    { key: 'classification', label: 'Classification', sortable: true },
    { key: 'updated_at', label: 'Updated', sortable: true, width: '120px' },
  ],
  project: [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'owner', label: 'Owner', sortable: true },
    { key: 'status', label: 'Status', sortable: true, isStatus: true },
    { key: 'classification', label: 'Classification', sortable: true },
    { key: 'start_date', label: 'Start', sortable: true, width: '110px' },
    { key: 'end_date', label: 'End', sortable: true, width: '110px' },
    { key: 'updated_at', label: 'Updated', sortable: true, width: '120px' },
  ],
};

/** Bulk actions available for each workspace type. */
const bulkActionsByType: Record<WorkspaceType, BulkAction[]> = {
  portfolio: [
    { key: 'export', label: 'Export', variant: 'default' },
    { key: 'archive', label: 'Archive', variant: 'danger', confirm: true, confirmMessage: 'Are you sure you want to archive the selected portfolios?' },
  ],
  program: [
    { key: 'export', label: 'Export', variant: 'default' },
    { key: 'archive', label: 'Archive', variant: 'danger', confirm: true, confirmMessage: 'Are you sure you want to archive the selected programs?' },
  ],
  project: [
    { key: 'export', label: 'Export', variant: 'default' },
    { key: 'change-status', label: 'Change Status', variant: 'primary' },
    { key: 'archive', label: 'Archive', variant: 'danger', confirm: true, confirmMessage: 'Are you sure you want to archive the selected projects?' },
  ],
};

interface SearchResponse {
  items: Array<{
    id: string;
    tenant_id: string;
    schema_name: string;
    schema_version: number;
    data: Record<string, unknown>;
    created_at: string;
    updated_at: string;
  }>;
  total: number;
  offset: number;
  limit: number;
  facets: Array<{ field: string; buckets: Array<{ value: string; count: number }> }>;
}

/** Seeded demo records shown when the API is unavailable. */
const seededRecords: Record<WorkspaceType, EntityRecord[]> = {
  portfolio: [
    { id: 'demo', tenant_id: 'demo', schema_name: 'portfolio', schema_version: 1, data: { name: 'Enterprise Transformation Portfolio', owner: 'PMO Office', status: 'Open', classification: 'Strategic' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    { id: 'cloud', tenant_id: 'demo', schema_name: 'portfolio', schema_version: 1, data: { name: 'Cloud Migration Portfolio', owner: 'Platform Office', status: 'Planning', classification: 'Tactical' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  ],
  program: [
    { id: 'demo', tenant_id: 'demo', schema_name: 'program', schema_version: 1, data: { name: 'Customer Experience Program', owner: 'Jane Alvarez', status: 'Execution', classification: 'Strategic' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    { id: 'supply-chain', tenant_id: 'demo', schema_name: 'program', schema_version: 1, data: { name: 'Supply Chain Optimization', owner: 'Marco Singh', status: 'Planning', classification: 'Operational' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  ],
  project: [
    { id: 'demo', tenant_id: 'demo', schema_name: 'project', schema_version: 1, data: { name: 'Digital Onboarding Revamp', owner: 'Maya Chen', status: 'Execution', classification: 'Strategic' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    { id: 'erp-uplift', tenant_id: 'demo', schema_name: 'project', schema_version: 1, data: { name: 'ERP Reporting Uplift', owner: 'Liam Patel', status: 'Planning', classification: 'Operational' }, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  ],
};

const PAGE_SIZE = 25;

export function WorkspaceDirectoryPage({ type }: WorkspaceDirectoryPageProps) {
  const navigate = useNavigate();

  // Search & filter state
  const [query, setQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [offset, setOffset] = useState(0);

  // Data state
  const [records, setRecords] = useState<EntityRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [facets, setFacets] = useState<Facet[]>([]);
  const [loading, setLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(false);

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const columns = columnsByType[type];
  const bulkActions = bulkActionsByType[type];

  // Reset state when workspace type changes
  useEffect(() => {
    setQuery('');
    setActiveFilters({});
    setSortBy('updated_at');
    setSortOrder('desc');
    setOffset(0);
    setSelectedIds(new Set());
    setUseFallback(false);
  }, [type]);

  // Fetch records via search endpoint
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      try {
        const body = {
          query: query.trim(),
          filters: activeFilters,
          sort_by: sortBy,
          sort_order: sortOrder,
        };
        const result = await requestJson<SearchResponse>(
          `/api/data/v1/entities/${type}/search?offset=${offset}&limit=${PAGE_SIZE}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
        );
        if (cancelled) return;
        setRecords(result.items);
        setTotal(result.total);
        setFacets(
          result.facets.map((f) => ({
            field: f.field,
            buckets: f.buckets.map((b) => ({ value: b.value, count: b.count })),
          })),
        );
        setUseFallback(false);
      } catch {
        if (cancelled) return;
        // Fall back to seeded records for offline/demo environments
        setUseFallback(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void fetchData();
    return () => {
      cancelled = true;
    };
  }, [type, query, activeFilters, sortBy, sortOrder, offset]);

  // Fallback: client-side filter/sort on seeded data
  const fallbackData = useMemo(() => {
    if (!useFallback) return null;
    let items = [...seededRecords[type]];
    const q = query.trim().toLowerCase();
    if (q) {
      items = items.filter((r) => {
        const haystack = Object.values(r.data).join(' ').toLowerCase();
        return haystack.includes(q) || r.id.toLowerCase().includes(q);
      });
    }
    for (const [field, values] of Object.entries(activeFilters)) {
      if (values.length > 0) {
        items = items.filter((r) => {
          const val = String(r.data[field] ?? '');
          return values.includes(val);
        });
      }
    }
    return { items, total: items.length };
  }, [useFallback, type, query, activeFilters]);

  const displayRecords = useFallback && fallbackData ? fallbackData.items : records;
  const displayTotal = useFallback && fallbackData ? fallbackData.total : total;

  const handleSortChange = useCallback((field: string, order: 'asc' | 'desc') => {
    setSortBy(field);
    setSortOrder(order);
    setOffset(0);
  }, []);

  const handlePageChange = useCallback((newOffset: number) => {
    setOffset(newOffset);
    setSelectedIds(new Set());
  }, []);

  const handleQueryChange = useCallback((q: string) => {
    setQuery(q);
    setOffset(0);
    setSelectedIds(new Set());
  }, []);

  const handleFiltersChange = useCallback((filters: Record<string, string[]>) => {
    setActiveFilters(filters);
    setOffset(0);
    setSelectedIds(new Set());
  }, []);

  const handleOpen = useCallback(
    (record: EntityRecord) => {
      navigate(`/${type}s/${encodeURIComponent(record.id)}`);
    },
    [navigate, type],
  );

  const handleBulkAction = useCallback(
    (actionKey: string) => {
      // Placeholder: in a real implementation this would call the appropriate API
      const ids = Array.from(selectedIds);
      console.info(`Bulk action "${actionKey}" on ${ids.length} ${type}(s):`, ids);
      setSelectedIds(new Set());
    },
    [selectedIds, type],
  );

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{labels[type]} Directory</h1>
        <p>Search, filter, and manage {pluralLabels[type]}.</p>
      </header>

      <FacetedFilter
        query={query}
        onQueryChange={handleQueryChange}
        facets={facets}
        activeFilters={activeFilters}
        onFiltersChange={handleFiltersChange}
        totalResults={displayTotal}
        searchPlaceholder={`Search ${pluralLabels[type]} by name, owner, or ID...`}
        entityLabel={pluralLabels[type]}
      />

      <BulkActions
        selectedCount={selectedIds.size}
        actions={bulkActions}
        onAction={handleBulkAction}
        onClearSelection={handleClearSelection}
        entityLabel={pluralLabels[type]}
      />

      {loading && displayRecords.length === 0 ? (
        <div className={styles.loadingState}>Loading {pluralLabels[type]}...</div>
      ) : (
        <EntityTable
          columns={columns}
          records={displayRecords}
          total={displayTotal}
          offset={offset}
          pageSize={PAGE_SIZE}
          onPageChange={handlePageChange}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSortChange={handleSortChange}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onOpen={handleOpen}
          emptyMessage={`No ${pluralLabels[type]} found matching your criteria.`}
          selectable
        />
      )}
    </div>
  );
}

export default WorkspaceDirectoryPage;
