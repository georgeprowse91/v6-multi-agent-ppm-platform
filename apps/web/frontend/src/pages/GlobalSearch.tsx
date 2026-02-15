import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  fetchGlobalSearch,
  type SearchResult,
  type SearchResultType,
} from '@/services/searchApi';
import type { DocumentSummary, LessonRecord } from '@/services/knowledgeApi';
import { tokenizeHighlight } from '@ppm/canvas-engine/security';
import styles from './GlobalSearch.module.css';

const TYPE_LABELS: Record<SearchResultType, string> = {
  document: 'Documents',
  project: 'Projects',
  knowledge: 'Knowledge Base',
  approval: 'Approvals',
  workflow: 'Workflows',
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

  const groupedResults = useMemo(() => {
    const groups: Record<SearchResultType, SearchResult[]> = {
      document: [],
      project: [],
      knowledge: [],
      approval: [],
      workflow: [],
    };
    filteredResults.forEach((result) => {
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
        });
        setTotal(response.total);
        setResults((prev) =>
          append ? prev.concat(response.results) : response.results
        );
      } catch (error) {
        console.error('Failed to load global search results', error);
      } finally {
        setLoading(false);
      }
    },
    [projectIds, query, selectedTypes]
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

  const renderDocumentCard = (result: SearchResult) => {
    const payload = result.payload as unknown as DocumentSummary;
    return (
      <li key={result.id} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{payload.name}</h3>
            <p>{payload.docType} · {payload.classification}</p>
          </div>
          <span className={styles.badge}>{payload.latestStatus}</span>
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
      <li key={result.id} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{payload.title}</h3>
            <p>
              {payload.stageName ?? 'General'} · Project {payload.projectId}
            </p>
          </div>
        </div>
        {result.highlights?.excerpt ? (
          <p className={styles.lessonDescription}>
            {renderHighlightedText(payload.description, result.highlights.excerpt)}
          </p>
        ) : (
          <p className={styles.lessonDescription}>{payload.description}</p>
        )}
        <div className={styles.chipRow}>
          {payload.tags.map((tag) => (
            <span key={`tag-${payload.lessonId}-${tag}`} className={styles.chip}>
              #{tag}
            </span>
          ))}
          {payload.topics.map((topic) => (
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
      <li key={result.id} className={styles.resultCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>{renderHighlightedText(result.title, result.highlights?.title)}</h3>
            <p>Project {result.projectId ?? 'N/A'}</p>
          </div>
        </div>
        <p className={styles.lessonDescription}>
          {renderHighlightedText(result.summary, result.highlights?.summary)}
        </p>
      </li>
    );
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Global Search</h1>
          <p>
            Search documents, projects, knowledge, approvals, and workflows across
            portfolios.
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
            placeholder="Search across the portfolio"
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
          <input
            className={styles.filterInput}
            value={projectFilter}
            onChange={(event) => setProjectFilter(event.target.value)}
            placeholder="Project IDs (comma separated)"
          />
        </div>
      </header>

      <div className={styles.resultsWrapper}>
        {loading && results.length === 0 && (
          <div className={styles.emptyState}>Searching...</div>
        )}
        {!loading && results.length === 0 && (
          <div className={styles.emptyState}>
            {query.trim()
              ? 'No results found. Try refining your filters.'
              : 'Enter a query to search across the portfolio.'}
          </div>
        )}

        {DEFAULT_TYPES.map((type) => (
          <section key={type} className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2>{TYPE_LABELS[type]}</h2>
              <span className={styles.countBadge}>{groupedResults[type].length}</span>
            </div>
            {groupedResults[type].length === 0 && (
              <div className={styles.emptyState}>No results yet.</div>
            )}
            {groupedResults[type].length > 0 && (
              <ul className={styles.resultList}>
                {groupedResults[type].map((result) => {
                  if (result.type === 'document') {
                    return renderDocumentCard(result);
                  }
                  if (result.type === 'knowledge') {
                    return renderKnowledgeCard(result);
                  }
                  return renderGenericCard(result);
                })}
              </ul>
            )}
          </section>
        ))}

        {hasMore && (
          <div className={styles.loadMore}>
            <button
              className={styles.secondaryButton}
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? 'Loading…' : 'Load more results'}
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
