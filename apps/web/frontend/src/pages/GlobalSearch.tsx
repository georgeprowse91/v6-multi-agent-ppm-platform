import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  fetchGlobalSearch,
  type SearchResult,
  type SearchResultType,
  type SourceSystem,
} from '@/services/searchApi';
import type { DocumentSummary, LessonRecord } from '@/services/knowledgeApi';
import { tokenizeHighlight } from '@ppm/canvas-engine/security';
import styles from './GlobalSearch.module.css';

const TYPE_LABELS: Record<string, string> = {
  document: 'Documents',
  project: 'Projects',
  knowledge: 'Knowledge Base',
  approval: 'Approvals',
  workflow: 'Workflows',
  issues: 'Jira Issues',
  pages: 'Confluence Pages',
  documents: 'SharePoint Documents',
  projects: 'SAP Projects',
  costs: 'SAP Costs',
  lists: 'SharePoint Lists',
};

const SOURCE_LABELS: Record<SourceSystem, string> = {
  local: 'Local',
  jira: 'Jira',
  confluence: 'Confluence',
  sharepoint: 'SharePoint',
  sap: 'SAP',
};

const SOURCE_COLORS: Record<SourceSystem, string> = {
  local: '#6b7280',
  jira: '#0052CC',
  confluence: '#1868DB',
  sharepoint: '#038387',
  sap: '#0070F2',
};

const DEFAULT_TYPES: SearchResultType[] = [
  'document',
  'project',
  'knowledge',
  'approval',
  'workflow',
];

const PAGE_SIZE = 12;

type DateRange = 'all' | '7d' | '30d' | '90d';

export function GlobalSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [query, setQuery] = useState(initialQuery);
  const [projectFilter, setProjectFilter] = useState(
    searchParams.get('projects') ?? ''
  );
  const [selectedTypes, setSelectedTypes] = useState<Set<SearchResultType>>(
    new Set(DEFAULT_TYPES)
  );
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [includeConnectors, setIncludeConnectors] = useState(true);
  const [connectorSources, setConnectorSources] = useState<string[]>([]);

  const projectIds = useMemo(
    () =>
      projectFilter
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean),
    [projectFilter]
  );

  const filteredResults = useMemo(() => {
    if (dateRange === 'all') {
      return results;
    }

    const days = Number(dateRange.replace('d', ''));
    const threshold = Date.now() - days * 24 * 60 * 60 * 1000;
    return results.filter((result) => {
      const updated = result.updatedAt;
      if (!updated) {
        return false;
      }
      const timestamp = new Date(updated).getTime();
      return !Number.isNaN(timestamp) && timestamp >= threshold;
    });
  }, [dateRange, results]);

  // Group results by source system
  const groupedBySource = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {};
    filteredResults.forEach((result) => {
      const source = result.sourceSystem || 'local';
      if (!groups[source]) {
        groups[source] = [];
      }
      groups[source].push(result);
    });
    return groups;
  }, [filteredResults]);

  // Also group by type for the existing view
  const allTypes = useMemo(() => {
    const types = new Set<string>();
    filteredResults.forEach((r) => types.add(r.type));
    return Array.from(types);
  }, [filteredResults]);

  const groupedByType = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {};
    filteredResults.forEach((result) => {
      if (!groups[result.type]) {
        groups[result.type] = [];
      }
      groups[result.type].push(result);
    });
    return groups;
  }, [filteredResults]);

  const loadResults = useCallback(
    async (offset = 0, append = false) => {
      if (!query.trim()) {
        setResults([]);
        setTotal(0);
        return;
      }
      setLoading(true);
      try {
        const response = await fetchGlobalSearch({
          query: query.trim(),
          types: Array.from(selectedTypes),
          projectIds,
          offset,
          limit: PAGE_SIZE,
          includeConnectors,
        });
        setTotal(response.total);
        setConnectorSources(response.connectors || []);
        setResults((prev) =>
          append ? prev.concat(response.results) : response.results
        );
      } catch (error) {
        console.error('Failed to load global search results', error);
      } finally {
        setLoading(false);
      }
    },
    [projectIds, query, selectedTypes, includeConnectors]
  );

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    const queryParam = params.get('q') ?? '';
    if (queryParam !== query) {
      setQuery(queryParam);
    }
    const projectsParam = params.get('projects') ?? '';
    if (projectsParam !== projectFilter) {
      setProjectFilter(projectsParam);
    }
  }, [projectFilter, query, searchParams]);

  useEffect(() => {
    if (query.trim()) {
      loadResults(0, false);
    } else {
      setResults([]);
      setTotal(0);
    }
  }, [loadResults, query, projectIds, selectedTypes]);

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (query.trim()) {
      params.set('q', query.trim());
    }
    if (projectFilter.trim()) {
      params.set('projects', projectFilter.trim());
    }
    setSearchParams(params);
  };

  const toggleType = (type: SearchResultType) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const handleLoadMore = () => {
    loadResults(results.length, true);
  };

  const hasMore = results.length < total;

  const renderSourceBadge = (source: SourceSystem) => {
    const color = SOURCE_COLORS[source] || '#6b7280';
    return (
      <span
        className={styles.sourceBadge}
        style={{ background: `${color}15`, color, borderColor: `${color}40` }}
      >
        {SOURCE_LABELS[source] || source}
      </span>
    );
  };

  const renderDocumentCard = (result: SearchResult) => {
    const payload = result.payload as unknown as DocumentSummary;
    return (
      <li key={`${result.id}-${result.sourceSystem}`} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{payload.name}</h3>
            <p>{payload.docType} · {payload.classification}</p>
          </div>
          <div className={styles.badgeRow}>
            {renderSourceBadge(result.sourceSystem)}
            <span className={styles.badge}>{payload.latestStatus}</span>
          </div>
        </div>
        <div className={styles.metaRow}>
          <span>Project {payload.projectId}</span>
          <span>Updated {new Date(payload.updatedAt).toLocaleString()}</span>
        </div>
        {result.highlights?.excerpt && (
          <p className={styles.excerpt}>
            {renderHighlightedText(
              result.summary,
              result.highlights.excerpt
            )}
          </p>
        )}
      </li>
    );
  };

  const renderKnowledgeCard = (result: SearchResult) => {
    const payload = result.payload as unknown as LessonRecord;
    return (
      <li key={`${result.id}-${result.sourceSystem}`} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{payload.title}</h3>
            <p>
              {payload.stageName ?? 'General'} · Project {payload.projectId}
            </p>
          </div>
          {renderSourceBadge(result.sourceSystem)}
        </div>
        {result.highlights?.excerpt ? (
          <p className={styles.lessonDescription}>
            {renderHighlightedText(payload.description, result.highlights.excerpt)}
          </p>
        ) : (
          <p className={styles.lessonDescription}>{payload.description}</p>
        )}
        <div className={styles.chipRow}>
          {payload.tags?.map((tag) => (
            <span key={`tag-${payload.lessonId}-${tag}`} className={styles.chip}>
              #{tag}
            </span>
          ))}
          {payload.topics?.map((topic) => (
            <span
              key={`topic-${payload.lessonId}-${topic}`}
              className={styles.chipAlt}
            >
              {topic}
            </span>
          ))}
        </div>
      </li>
    );
  };

  const renderConnectorCard = (result: SearchResult) => {
    return (
      <li key={`${result.id}-${result.sourceSystem}`} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>
              {result.sourceUrl ? (
                <a
                  href={result.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.resultLink}
                >
                  {result.title}
                </a>
              ) : (
                result.title
              )}
            </h3>
            <p>{result.summary}</p>
          </div>
          <div className={styles.badgeRow}>
            {renderSourceBadge(result.sourceSystem)}
            <span className={styles.typeBadge}>
              {TYPE_LABELS[result.type] || result.type}
            </span>
          </div>
        </div>
        {result.projectId && (
          <div className={styles.metaRow}>
            <span>Project {result.projectId}</span>
            {result.updatedAt && (
              <span>Updated {new Date(result.updatedAt).toLocaleString()}</span>
            )}
          </div>
        )}
      </li>
    );
  };

  const renderHighlightedText = (text: string, highlight?: string | null) => {
    const tokens = tokenizeHighlight(text, highlight);

    return (
      <span>
        {tokens.map((token, index) =>
          token.highlighted ? (
            <mark key={`${token.text}-${index}`}>{token.text}</mark>
          ) : (
            <span key={`${token.text}-${index}`}>{token.text}</span>
          )
        )}
      </span>
    );
  };

  const renderGenericCard = (result: SearchResult) => {
    return (
      <li key={`${result.id}-${result.sourceSystem}`} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{renderHighlightedText(result.title, result.highlights?.title)}</h3>
            <p>Project {result.projectId ?? 'N/A'}</p>
          </div>
          {renderSourceBadge(result.sourceSystem)}
        </div>
        <p className={styles.lessonDescription}>
          {renderHighlightedText(result.summary, result.highlights?.summary)}
        </p>
      </li>
    );
  };

  const renderResultCard = (result: SearchResult) => {
    if (result.sourceSystem && result.sourceSystem !== 'local') {
      return renderConnectorCard(result);
    }
    if (result.type === 'document') {
      return renderDocumentCard(result);
    }
    if (result.type === 'knowledge') {
      return renderKnowledgeCard(result);
    }
    return renderGenericCard(result);
  };

  const sourceEntries = Object.entries(groupedBySource);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Cross-System Search</h1>
          <p>
            Search documents, projects, knowledge, and connected external systems
            across your portfolio.
          </p>
        </div>
        <form className={styles.searchControls} onSubmit={(event) => {
          event.preventDefault();
          handleSearch();
        }}>
          <label className={styles.visuallyHidden} htmlFor="global-search-input">
            Global search query
          </label>
          <input
            id="global-search-input"
            className={styles.searchInput}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search across all systems..."
          />
          <button className={styles.primaryButton} type="submit">
            Search
          </button>
        </form>
        <div className={styles.filterRow}>
          <div className={styles.filterGroup}>
            {DEFAULT_TYPES.map((type) => (
              <label key={type} className={styles.filterChip}>
                <input
                  type="checkbox"
                  checked={selectedTypes.has(type)}
                  onChange={() => toggleType(type)}
                />
                {TYPE_LABELS[type]}
              </label>
            ))}
          </div>
          <div className={styles.filterGroup}>
            {(['all', '7d', '30d', '90d'] as DateRange[]).map((range) => (
              <button
                key={range}
                type="button"
                className={`${styles.dateChip} ${dateRange === range ? styles.dateChipActive : ''}`.trim()}
                onClick={() => setDateRange(range)}
              >
                {range === 'all' ? 'Any time' : `Last ${range.replace('d', ' days')}`}
              </button>
            ))}
          </div>
          <label className={styles.filterChip}>
            <input
              type="checkbox"
              checked={includeConnectors}
              onChange={() => setIncludeConnectors((prev) => !prev)}
            />
            Include external systems
          </label>
          <input
            className={styles.filterInput}
            value={projectFilter}
            onChange={(event) => setProjectFilter(event.target.value)}
            placeholder="Project IDs (comma separated)"
          />
        </div>
        {connectorSources.length > 0 && (
          <div className={styles.connectorBar}>
            <span className={styles.connectorLabel}>Connected sources:</span>
            {connectorSources.map((src) => (
              <span key={src} className={styles.connectorChip}>
                {SOURCE_LABELS[src as SourceSystem] || src}
              </span>
            ))}
          </div>
        )}
      </header>

      <div className={styles.resultsWrapper}>
        {loading && results.length === 0 && (
          <div className={styles.emptyState}>Searching across all systems...</div>
        )}
        {!loading && results.length === 0 && (
          <div className={styles.emptyState}>
            {query.trim()
              ? 'No results found. Try refining your filters or enabling external systems.'
              : 'Enter a query to search across the portfolio and connected systems.'}
          </div>
        )}

        {/* Group by source system */}
        {sourceEntries.map(([source, items]) => (
          <section key={source} className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2>{SOURCE_LABELS[source as SourceSystem] || source}</h2>
              <span className={styles.countBadge}>{items.length}</span>
              {source !== 'local' && (
                <span className={styles.externalTag}>External</span>
              )}
            </div>
            <ul className={styles.resultList}>
              {items.map((result) => renderResultCard(result))}
            </ul>
          </section>
        ))}

        {/* Grouped by type fallback when no source groups */}
        {sourceEntries.length === 0 && allTypes.map((type) => {
          const items = groupedByType[type] || [];
          if (items.length === 0) return null;
          return (
            <section key={type} className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2>{TYPE_LABELS[type] || type}</h2>
                <span className={styles.countBadge}>{items.length}</span>
              </div>
              <ul className={styles.resultList}>
                {items.map((result) => renderResultCard(result))}
              </ul>
            </section>
          );
        })}

        {hasMore && (
          <div className={styles.loadMore}>
            <button
              className={styles.secondaryButton}
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Load more results'}
            </button>
            <span className={styles.resultsMeta}>
              Showing {results.length} of {total}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default GlobalSearchPage;
