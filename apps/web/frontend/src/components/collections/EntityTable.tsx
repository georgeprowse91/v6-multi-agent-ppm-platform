import { useCallback, useMemo } from 'react';
import styles from './EntityTable.module.css';

export interface ColumnDef {
  /** Field key to extract from entity data */
  key: string;
  /** Column header label */
  label: string;
  /** Whether this column is sortable */
  sortable?: boolean;
  /** Render as status badge */
  isStatus?: boolean;
  /** Render as ID (monospace) */
  isId?: boolean;
  /** Custom width */
  width?: string;
}

export interface EntityRecord {
  id: string;
  tenant_id: string;
  schema_name: string;
  schema_version: number;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EntityTableProps {
  /** Column definitions */
  columns: ColumnDef[];
  /** Entity records to display */
  records: EntityRecord[];
  /** Total count for pagination */
  total: number;
  /** Current page offset */
  offset: number;
  /** Page size */
  pageSize: number;
  /** Callback on page change */
  onPageChange: (offset: number) => void;
  /** Current sort field */
  sortBy: string;
  /** Sort direction */
  sortOrder: 'asc' | 'desc';
  /** Callback on sort change */
  onSortChange: (field: string, order: 'asc' | 'desc') => void;
  /** Currently selected IDs */
  selectedIds: Set<string>;
  /** Callback on selection change */
  onSelectionChange: (ids: Set<string>) => void;
  /** Callback when "Open" is clicked on a row */
  onOpen?: (record: EntityRecord) => void;
  /** Show empty state message */
  emptyMessage?: string;
  /** Enable row selection checkboxes */
  selectable?: boolean;
}

function statusClassName(status: string): string {
  const normalized = status.toLowerCase().replace(/[\s_-]+/g, '');
  const map: Record<string, string> = {
    open: styles.statusOpen,
    planning: styles.statusPlanning,
    execution: styles.statusExecution,
    monitoring: styles.statusMonitoring,
    closed: styles.statusClosed,
    todo: styles.statusTodo,
    inprogress: styles.statusInProgress,
    in_progress: styles.statusInProgress,
    done: styles.statusDone,
    blocked: styles.statusBlocked,
    mitigated: styles.statusMitigated,
    mitigating: styles.statusMitigating,
    initiated: styles.statusInitiated,
  };
  return map[normalized] || styles.statusDefault;
}

function CellValue({ column, value }: { column: ColumnDef; value: unknown }) {
  const str = value == null ? '' : String(value);

  if (column.isStatus && str) {
    return (
      <span className={`${styles.statusBadge} ${statusClassName(str)}`}>
        {str.replace(/_/g, ' ')}
      </span>
    );
  }

  if (column.isId) {
    return <span className={styles.idCell}>{str}</span>;
  }

  return <>{str}</>;
}

export function EntityTable({
  columns,
  records,
  total,
  offset,
  pageSize,
  onPageChange,
  sortBy,
  sortOrder,
  onSortChange,
  selectedIds,
  onSelectionChange,
  onOpen,
  emptyMessage = 'No records found.',
  selectable = true,
}: EntityTableProps) {
  const allSelected = records.length > 0 && records.every((r) => selectedIds.has(r.id));

  const toggleAll = useCallback(() => {
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(records.map((r) => r.id)));
    }
  }, [allSelected, records, onSelectionChange]);

  const toggleOne = useCallback(
    (id: string) => {
      const next = new Set(selectedIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      onSelectionChange(next);
    },
    [selectedIds, onSelectionChange],
  );

  const handleSort = useCallback(
    (field: string) => {
      if (sortBy === field) {
        onSortChange(field, sortOrder === 'asc' ? 'desc' : 'asc');
      } else {
        onSortChange(field, 'desc');
      }
    },
    [sortBy, sortOrder, onSortChange],
  );

  const currentPage = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.ceil(total / pageSize);

  const getValue = useMemo(
    () => (record: EntityRecord, key: string): unknown => {
      if (key === 'id') return record.id;
      if (key === 'updated_at') return new Date(record.updated_at).toLocaleDateString();
      if (key === 'created_at') return new Date(record.created_at).toLocaleDateString();
      return record.data[key];
    },
    [],
  );

  return (
    <div>
      <div className={styles.wrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              {selectable && (
                <th className={styles.checkboxCell}>
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Select all"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  {col.label}
                  {sortBy === col.key && (
                    <span className={styles.sortIndicator}>
                      {sortOrder === 'asc' ? '\u25B2' : '\u25BC'}
                    </span>
                  )}
                </th>
              ))}
              {onOpen && <th className={styles.actionCell} />}
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (selectable ? 1 : 0) + (onOpen ? 1 : 0)}
                  className={styles.emptyState}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              records.map((record) => (
                <tr
                  key={record.id}
                  className={selectedIds.has(record.id) ? styles.rowSelected : ''}
                >
                  {selectable && (
                    <td className={styles.checkboxCell}>
                      <input
                        type="checkbox"
                        className={styles.checkbox}
                        checked={selectedIds.has(record.id)}
                        onChange={() => toggleOne(record.id)}
                        aria-label={`Select ${record.id}`}
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td key={col.key}>
                      <CellValue column={col} value={getValue(record, col.key)} />
                    </td>
                  ))}
                  {onOpen && (
                    <td className={styles.actionCell}>
                      <button
                        type="button"
                        className={styles.openBtn}
                        onClick={() => onOpen(record)}
                      >
                        Open
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > pageSize && (
        <div className={styles.pagination}>
          <div className={styles.pageInfo}>
            <span>
              Page {currentPage} of {totalPages} ({total} total)
            </span>
          </div>
          <div className={styles.pageInfo}>
            <button
              type="button"
              className={styles.pageBtn}
              disabled={offset === 0}
              onClick={() => onPageChange(Math.max(0, offset - pageSize))}
            >
              Previous
            </button>
            <button
              type="button"
              className={styles.pageBtn}
              disabled={offset + pageSize >= total}
              onClick={() => onPageChange(offset + pageSize)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default EntityTable;
