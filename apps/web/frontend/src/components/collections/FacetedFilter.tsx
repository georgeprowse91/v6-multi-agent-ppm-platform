import { useCallback } from 'react';
import styles from './FacetedFilter.module.css';

export interface FacetBucket {
  value: string;
  count: number;
}

export interface Facet {
  field: string;
  buckets: FacetBucket[];
}

export interface FacetedFilterProps {
  /** Search query string */
  query: string;
  /** Callback when search query changes */
  onQueryChange: (query: string) => void;
  /** Available facets with counts */
  facets: Facet[];
  /** Currently active filter selections: field -> values[] */
  activeFilters: Record<string, string[]>;
  /** Callback when filters change */
  onFiltersChange: (filters: Record<string, string[]>) => void;
  /** Total result count */
  totalResults: number;
  /** Placeholder text for search input */
  searchPlaceholder?: string;
  /** Entity type label for display */
  entityLabel?: string;
}

function formatFieldLabel(field: string): string {
  return field
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function FacetedFilter({
  query,
  onQueryChange,
  facets,
  activeFilters,
  onFiltersChange,
  totalResults,
  searchPlaceholder = 'Search...',
  entityLabel = 'items',
}: FacetedFilterProps) {
  const toggleFilter = useCallback(
    (field: string, value: string) => {
      const current = activeFilters[field] || [];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      const next = { ...activeFilters };
      if (updated.length === 0) {
        delete next[field];
      } else {
        next[field] = updated;
      }
      onFiltersChange(next);
    },
    [activeFilters, onFiltersChange],
  );

  const removeFilter = useCallback(
    (field: string, value: string) => {
      const current = activeFilters[field] || [];
      const updated = current.filter((v) => v !== value);
      const next = { ...activeFilters };
      if (updated.length === 0) {
        delete next[field];
      } else {
        next[field] = updated;
      }
      onFiltersChange(next);
    },
    [activeFilters, onFiltersChange],
  );

  const clearAll = useCallback(() => {
    onQueryChange('');
    onFiltersChange({});
  }, [onQueryChange, onFiltersChange]);

  const hasActiveFilters = query.trim() !== '' || Object.keys(activeFilters).length > 0;

  const allActiveEntries: Array<{ field: string; value: string }> = [];
  for (const [field, values] of Object.entries(activeFilters)) {
    for (const value of values) {
      allActiveEntries.push({ field, value });
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.searchRow}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder={searchPlaceholder}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
        />
        {hasActiveFilters && (
          <button type="button" className={styles.clearBtn} onClick={clearAll}>
            Clear all
          </button>
        )}
      </div>

      {facets.length > 0 && (
        <div className={styles.facetGroups}>
          {facets.map((facet) => (
            <div key={facet.field} className={styles.facetGroup}>
              <span className={styles.facetLabel}>{formatFieldLabel(facet.field)}</span>
              <div className={styles.facetOptions}>
                {facet.buckets.map((bucket) => {
                  const isActive = (activeFilters[facet.field] || []).includes(bucket.value);
                  return (
                    <button
                      key={bucket.value}
                      type="button"
                      className={`${styles.facetChip} ${isActive ? styles.facetChipActive : ''}`}
                      onClick={() => toggleFilter(facet.field, bucket.value)}
                    >
                      {bucket.value}
                      <span className={styles.facetCount}>({bucket.count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {allActiveEntries.length > 0 && (
        <div className={styles.activeFilters}>
          <span className={styles.activeFilterLabel}>Filters:</span>
          {allActiveEntries.map(({ field, value }) => (
            <span key={`${field}:${value}`} className={styles.activeFilterTag}>
              {formatFieldLabel(field)}: {value}
              <span
                className={styles.removeFilter}
                role="button"
                tabIndex={0}
                onClick={() => removeFilter(field, value)}
                onKeyDown={(e) => e.key === 'Enter' && removeFilter(field, value)}
              >
                x
              </span>
            </span>
          ))}
        </div>
      )}

      <span className={styles.resultCount}>
        {totalResults} {entityLabel} found
      </span>
    </div>
  );
}

export default FacetedFilter;
