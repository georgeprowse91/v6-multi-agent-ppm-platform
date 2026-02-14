import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Connector } from '@/store/connectors/types';
import styles from './ConnectorDetailPage.module.css';

export function ConnectorDetailPage() {
  const { connector_type_id } = useParams();
  const [connector, setConnector] = useState<Connector | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!connector_type_id) return;
    const load = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/v1/connectors/${encodeURIComponent(connector_type_id)}`);
        if (!response.ok) throw new Error(`Failed to load connector (${response.status})`);
        const data = (await response.json()) as Connector;
        setConnector({
          ...data,
          supported_objects: data.supported_objects ?? [],
          limitations: data.limitations ?? [],
          auth_requirements: data.auth_requirements ?? [],
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load connector details');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [connector_type_id]);

  if (loading) return <div className={styles.state}>Loading connector details…</div>;
  if (error || !connector) return <div className={styles.stateError}>{error ?? 'Connector not found'}</div>;

  return (
    <div className={styles.page}>
      <Link to="/config/connectors" className={styles.backLink}>← Back to connector catalog</Link>
      <h1>{connector.name}</h1>
      <p>{connector.description}</p>
      <div className={styles.grid}>
        <section className={styles.card}>
          <h2>Certification & status</h2>
          <p>Status: <strong>{connector.status}</strong></p>
          <p>Health: <strong>{connector.health_status}</strong></p>
          <p>Last health check: <strong>{connector.last_sync_at ?? 'Not yet tested'}</strong></p>
        </section>
        <section className={styles.card}>
          <h2>Authentication requirements</h2>
          <ul>{(connector.auth_requirements.length ? connector.auth_requirements : [connector.auth_type]).map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
        <section className={styles.card}>
          <h2>Supported objects</h2>
          <ul>{(connector.supported_objects.length ? connector.supported_objects : ['No objects declared']).map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
        <section className={styles.card}>
          <h2>Limitations</h2>
          <ul>{(connector.limitations.length ? connector.limitations : ['No known limitations declared']).map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      </div>
    </div>
  );
}

export default ConnectorDetailPage;
