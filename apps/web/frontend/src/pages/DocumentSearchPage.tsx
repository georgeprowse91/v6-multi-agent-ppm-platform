import { useCallback, useEffect, useState } from 'react';
import { useMethodologyStore } from '@/store/methodology';
import {
  fetchDocuments,
  fetchDocumentVersions,
  type DocumentSummary,
  type DocumentVersion,
} from '@/services/knowledgeApi';
import styles from './DocumentSearchPage.module.css';

export function DocumentSearchPage() {
  const { projectMethodology } = useMethodologyStore();
  const projectId = projectMethodology.projectId;
  const projectName = projectMethodology.projectName;

  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentSummary | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [versionLoading, setVersionLoading] = useState(false);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const results = await fetchDocuments(projectId, query.trim() || undefined);
      setDocuments(results);
      if (results.length === 0) {
        setSelectedDoc(null);
        setVersions([]);
      }
    } catch (error) {
      console.error('Failed to load documents', error);
    } finally {
      setLoading(false);
    }
  }, [projectId, query]);

  const loadVersions = useCallback(async (documentId: string) => {
    setVersionLoading(true);
    try {
      const results = await fetchDocumentVersions(documentId);
      setVersions(results);
    } catch (error) {
      console.error('Failed to load versions', error);
    } finally {
      setVersionLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleSelectDoc = async (doc: DocumentSummary) => {
    setSelectedDoc(doc);
    await loadVersions(doc.documentId);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Document Repository</h1>
          <p>
            Project-scoped document search for <strong>{projectName}</strong>.
          </p>
        </div>
        <div className={styles.searchControls}>
          <input
            className={styles.searchInput}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by title or content"
          />
          <button className={styles.primaryButton} onClick={loadDocuments}>
            Search
          </button>
        </div>
      </header>

      <div className={styles.layout}>
        <section className={styles.listSection}>
          <div className={styles.sectionHeader}>
            <h2>Documents</h2>
            <button className={styles.secondaryButton} onClick={loadDocuments}>
              Refresh
            </button>
          </div>

          {loading && <div className={styles.emptyState}>Loading documents...</div>}
          {!loading && documents.length === 0 && (
            <div className={styles.emptyState}>No documents found yet.</div>
          )}

          <ul className={styles.cardList}>
            {documents.map((doc) => (
              <li
                key={doc.documentId}
                className={`${styles.card} ${
                  selectedDoc?.documentId === doc.documentId ? styles.activeCard : ''
                }`}
                onClick={() => handleSelectDoc(doc)}
              >
                <div className={styles.cardHeader}>
                  <div>
                    <h3>{doc.name}</h3>
                    <p>{doc.docType} · {doc.classification}</p>
                  </div>
                  <span className={styles.badge}>{doc.latestStatus}</span>
                </div>
                <div className={styles.metaRow}>
                  <span>Latest v{doc.latestVersion}</span>
                  <span>Updated {new Date(doc.updatedAt).toLocaleString()}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <aside className={styles.detailSection}>
          <h2>Versions</h2>
          {!selectedDoc && (
            <div className={styles.emptyState}>
              Select a document to review versions.
            </div>
          )}
          {selectedDoc && (
            <div className={styles.detailCard}>
              <h3>{selectedDoc.name}</h3>
              <p className={styles.detailSubtitle}>
                {selectedDoc.docType} · {selectedDoc.classification}
              </p>
              {versionLoading && <div className={styles.emptyState}>Loading versions...</div>}
              {!versionLoading && versions.length === 0 && (
                <div className={styles.emptyState}>No versions recorded yet.</div>
              )}
              <ul className={styles.versionList}>
                {versions.map((version) => (
                  <li key={`${version.documentId}-${version.version}`} className={styles.versionCard}>
                    <div>
                      <strong>v{version.version}</strong> · {version.status}
                    </div>
                    <div className={styles.versionMeta}>
                      {new Date(version.createdAt).toLocaleString()}
                    </div>
                    <p className={styles.versionSnippet}>
                      {version.content.slice(0, 200)}
                      {version.content.length > 200 ? '…' : ''}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
