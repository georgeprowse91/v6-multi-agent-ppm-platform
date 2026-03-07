import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import styles from './IntakeStatusPage.module.css';

const API_BASE = '/v1';

interface IntakeRequest {
  request_id: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  project_id?: string | null;
  sponsor: {
    name: string;
    email: string;
    department: string;
    title?: string | null;
  };
  business_case: {
    summary: string;
    justification: string;
    expected_benefits: string;
    estimated_budget?: string | null;
  };
  success_criteria: {
    metrics: string;
    target_date?: string | null;
    risks?: string | null;
  };
  attachments: {
    summary: string;
    links: string[];
  };
  reviewers: string[];
  decision?: {
    decision: 'approved' | 'rejected';
    reviewer_id: string;
    comments?: string | null;
    decided_at: string;
  } | null;
}

export function IntakeStatusPage() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const [request, setRequest] = useState<IntakeRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingProject, setCreatingProject] = useState(false);

  useEffect(() => {
    const fetchRequest = async () => {
      if (!requestId) return;
      setLoading(true);
      try {
        const response = await fetch(`${API_BASE}/api/intake/${requestId}`);
        if (!response.ok) {
          throw new Error('Unable to load intake status.');
        }
        const data = await response.json();
        setRequest(data);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unable to load intake status.';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchRequest();
  }, [requestId]);

  if (loading) {
    return <div className={styles.loading}>Loading status...</div>;
  }

  if (error || !request) {
    return (
      <div className={styles.error}>
        <p>{error ?? 'Intake request not found.'}</p>
        <Link to="/intake/new" className={styles.linkButton}>
          Start a new intake
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Intake request status</h1>
          <p>Track the approval workflow for request {request.request_id}.</p>
        </div>
        <span className={`${styles.status} ${styles[request.status]}`}>
          {request.status}
        </span>
      </header>

      <section className={styles.summaryGrid}>
        <div className={styles.card}>
          <h2>Sponsor</h2>
          <p>{request.sponsor.name}</p>
          <p className={styles.muted}>{request.sponsor.department}</p>
          <p className={styles.muted}>{request.sponsor.email}</p>
        </div>
        <div className={styles.card}>
          <h2>Reviewers</h2>
          {request.reviewers.length > 0 ? (
            <ul>
              {request.reviewers.map((reviewer) => (
                <li key={reviewer}>{reviewer}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.muted}>No designated reviewers listed.</p>
          )}
        </div>
        <div className={styles.card}>
          <h2>Decision</h2>
          {request.decision ? (
            <div>
              <p>
                {request.decision.decision} by {request.decision.reviewer_id}
              </p>
              {request.decision.comments && (
                <p className={styles.muted}>{request.decision.comments}</p>
              )}
            </div>
          ) : (
            <p className={styles.muted}>Awaiting reviewer feedback.</p>
          )}
        </div>
      </section>

      {request.status === 'approved' && (
        <section className={styles.approvalActions}>
          {request.project_id ? (
            <div className={styles.projectCreated}>
              <h2>Project Created</h2>
              <p>Project <strong>{request.project_id}</strong> has been created from this intake request.</p>
              <div className={styles.projectActionRow}>
                <Link to={`/projects/${request.project_id}`} className={styles.linkButton}>
                  Open Project
                </Link>
                <Link to={`/projects/${request.project_id}/config`} className={styles.secondaryLink}>
                  Project Settings
                </Link>
              </div>
            </div>
          ) : (
            <div className={styles.setupPrompt}>
              <h2>Ready for Setup</h2>
              <p>This intake request has been approved. Configure the project using the setup wizard.</p>
              <div className={styles.projectActionRow}>
                <button
                  className={styles.configureBtn}
                  disabled={creatingProject}
                  onClick={async () => {
                    setCreatingProject(true);
                    try {
                      const resp = await fetch(`${API_BASE}/api/project-setup/create-from-intake`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ intake_request_id: request.request_id }),
                      });
                      if (resp.ok) {
                        const data = await resp.json();
                        navigate(`/projects/new?intake=${request.request_id}&project_id=${data.project_id || ''}`);
                      } else {
                        navigate(`/projects/new?intake=${request.request_id}`);
                      }
                    } catch {
                      navigate(`/projects/new?intake=${request.request_id}`);
                    } finally {
                      setCreatingProject(false);
                    }
                  }}
                >
                  {creatingProject ? 'Setting up...' : 'Configure Project'}
                </button>
                <Link to={`/projects/new?intake=${request.request_id}`} className={styles.secondaryLink}>
                  Go to Setup Wizard
                </Link>
              </div>
            </div>
          )}
        </section>
      )}

      <section className={styles.detailSection}>
        <div className={styles.detailCard}>
          <h2>Business case</h2>
          <p>{request.business_case.summary}</p>
          <p className={styles.muted}>{request.business_case.justification}</p>
          <p className={styles.muted}>{request.business_case.expected_benefits}</p>
        </div>
        <div className={styles.detailCard}>
          <h2>Success criteria</h2>
          <p>{request.success_criteria.metrics}</p>
          {request.success_criteria.target_date && (
            <p className={styles.muted}>Target date: {request.success_criteria.target_date}</p>
          )}
          {request.success_criteria.risks && (
            <p className={styles.muted}>Risks: {request.success_criteria.risks}</p>
          )}
        </div>
        <div className={styles.detailCard}>
          <h2>Attachments</h2>
          <p>{request.attachments.summary}</p>
          {request.attachments.links.length > 0 ? (
            <ul>
              {request.attachments.links.map((link) => (
                <li key={link}>{link}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.muted}>No links provided.</p>
          )}
        </div>
      </section>

      <div className={styles.footerActions}>
        <Link to="/intake/new" className={styles.linkButton}>
          Submit another request
        </Link>
        <Link to="/intake/approvals" className={styles.secondaryLink}>
          View intake approvals
        </Link>
      </div>
    </div>
  );
}

export default IntakeStatusPage;
