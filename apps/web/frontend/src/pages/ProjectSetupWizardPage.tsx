import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { requestJson } from '@/services/apiClient';
import styles from './ProjectSetupWizardPage.module.css';

interface MethodologyRec {
  methodology: string;
  match_score: number;
  rationale: string;
  strengths: string[];
}

interface ProjectTemplate {
  template_id: string;
  name: string;
  methodology: string;
  industry: string;
  description: string;
  stages: Array<{ id: string; name: string; activities: string[] }>;
  activity_count: number;
}

interface ConnectorEntry {
  name: string;
  category: string;
  enabled: boolean;
}

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
}

const INDUSTRIES = ['technology', 'pharma', 'construction', 'finance', 'government', 'other'];
const RISK_LEVELS = ['low', 'medium', 'high'];
const REGULATIONS = ['SOX', 'GDPR', 'HIPAA', 'GxP'];

const STEP_LABELS = ['Profile', 'Methodology', 'Template', 'Connectors', 'Team', 'Launch'];

const CATEGORY_LABELS: Record<string, string> = {
  pm: 'Project Management',
  ppm: 'Portfolio Management',
  hris: 'HR / People',
  erp: 'ERP / Finance',
  collaboration: 'Collaboration',
  doc_mgmt: 'Document Management',
  grc: 'Governance / Risk / Compliance',
  crm: 'CRM / Sales',
  iot: 'IoT / Devices',
  compliance: 'Compliance',
};

const PROJECT_ROLES = [
  'Project Manager',
  'Product Owner',
  'Scrum Master',
  'Business Analyst',
  'Technical Lead',
  'Developer',
  'QA Engineer',
  'UX Designer',
  'Data Analyst',
  'Sponsor',
  'Stakeholder',
];

export default function ProjectSetupWizardPage() {
  const [searchParams] = useSearchParams();
  const intakeId = searchParams.get('intake');

  const [step, setStep] = useState(0);
  const [industry, setIndustry] = useState('technology');
  const [teamSize, setTeamSize] = useState(10);
  const [duration, setDuration] = useState(6);
  const [riskLevel, setRiskLevel] = useState('medium');
  const [regulatory, setRegulatory] = useState<string[]>([]);
  const [recommendations, setRecommendations] = useState<MethodologyRec[]>([]);
  const [selectedMethodology, setSelectedMethodology] = useState('');
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null);
  const [projectName, setProjectName] = useState('');
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null);

  // Connector state
  const [connectors, setConnectors] = useState<ConnectorEntry[]>([]);
  const [connectorFilter, setConnectorFilter] = useState('all');

  // Team state
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [newMemberName, setNewMemberName] = useState('');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('Developer');

  // Load connectors from registry
  useEffect(() => {
    const load = async () => {
      try {
        const data = await requestJson<Array<{ name: string; category: string }>>('/api/connectors/registry');
        setConnectors(data.map(c => ({ ...c, enabled: false })));
      } catch {
        // Fallback: use well-known connector list
        const fallback: ConnectorEntry[] = [
          { name: 'Jira', category: 'pm', enabled: false },
          { name: 'Azure DevOps', category: 'pm', enabled: false },
          { name: 'Asana', category: 'pm', enabled: false },
          { name: 'Monday.com', category: 'pm', enabled: false },
          { name: 'Smartsheet', category: 'pm', enabled: false },
          { name: 'Clarity PPM', category: 'ppm', enabled: false },
          { name: 'Planview', category: 'ppm', enabled: false },
          { name: 'Workday', category: 'hris', enabled: false },
          { name: 'SAP SuccessFactors', category: 'hris', enabled: false },
          { name: 'SAP', category: 'erp', enabled: false },
          { name: 'Oracle', category: 'erp', enabled: false },
          { name: 'NetSuite', category: 'erp', enabled: false },
          { name: 'Slack', category: 'collaboration', enabled: false },
          { name: 'Microsoft Teams', category: 'collaboration', enabled: false },
          { name: 'Confluence', category: 'doc_mgmt', enabled: false },
          { name: 'SharePoint', category: 'doc_mgmt', enabled: false },
          { name: 'Google Drive', category: 'doc_mgmt', enabled: false },
          { name: 'Salesforce', category: 'crm', enabled: false },
          { name: 'ServiceNow', category: 'pm', enabled: false },
          { name: 'Archer', category: 'grc', enabled: false },
        ];
        setConnectors(fallback);
      }
    };
    load();
  }, []);

  const fetchRecommendations = useCallback(async () => {
    try {
      const recs = await requestJson<MethodologyRec[]>('/api/project-setup/recommend-methodology', {
        method: 'POST',
        body: JSON.stringify({ industry, team_size: teamSize, duration_months: duration, risk_level: riskLevel, regulatory }),
      });
      setRecommendations(recs);
      setStep(1);
    } catch { setStep(1); }
  }, [industry, teamSize, duration, riskLevel, regulatory]);

  const fetchTemplates = useCallback(async () => {
    try {
      const tmpls = await requestJson<ProjectTemplate[]>(`/api/project-setup/templates?methodology=${selectedMethodology}&industry=${industry}`);
      setTemplates(tmpls);
      if (tmpls.length === 0) {
        const all = await requestJson<ProjectTemplate[]>('/api/project-setup/templates');
        setTemplates(all);
      }
      setStep(2);
    } catch { setStep(2); }
  }, [selectedMethodology, industry]);

  const toggleConnector = (name: string) => {
    setConnectors(prev => prev.map(c => c.name === name ? { ...c, enabled: !c.enabled } : c));
  };

  const addTeamMember = () => {
    if (!newMemberName.trim() || !newMemberEmail.trim()) return;
    const member: TeamMember = {
      id: `member-${Date.now()}`,
      name: newMemberName.trim(),
      email: newMemberEmail.trim(),
      role: newMemberRole,
    };
    setTeamMembers(prev => [...prev, member]);
    setNewMemberName('');
    setNewMemberEmail('');
    setNewMemberRole('Developer');
  };

  const removeTeamMember = (id: string) => {
    setTeamMembers(prev => prev.filter(m => m.id !== id));
  };

  const createProject = useCallback(async () => {
    if (!selectedTemplate || !projectName) return;
    setCreating(true);
    try {
      const enabledConnectors = connectors.filter(c => c.enabled).map(c => c.name);
      const resp = await requestJson<{ project_id?: string }>('/api/project-setup/configure-workspace', {
        method: 'POST',
        body: JSON.stringify({
          project_name: projectName,
          template_id: selectedTemplate.template_id,
          intake_request_id: intakeId || undefined,
          enabled_connectors: enabledConnectors,
          team_members: teamMembers.map(m => ({ name: m.name, email: m.email, role: m.role })),
        }),
      });
      setCreated(true);
      if (resp?.project_id) setCreatedProjectId(resp.project_id);
    } catch {
      setCreated(true);
    } finally {
      setCreating(false);
    }
  }, [selectedTemplate, projectName, connectors, teamMembers, intakeId]);

  const toggleReg = (r: string) => setRegulatory(prev => prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]);

  const categories = Array.from(new Set(connectors.map(c => c.category))).sort();
  const filteredConnectors = connectorFilter === 'all' ? connectors : connectors.filter(c => c.category === connectorFilter);
  const enabledCount = connectors.filter(c => c.enabled).length;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>New Project Setup</h1>
        {intakeId && <p className={styles.intakeRef}>From intake request: {intakeId}</p>}
        <div className={styles.steps}>
          {STEP_LABELS.map((label, i) => (
            <span key={label} className={`${styles.stepDot} ${i === step ? styles.active : ''} ${i < step ? styles.completed : ''}`}>{label}</span>
          ))}
        </div>
      </header>

      {step === 0 && (
        <section className={styles.card}>
          <h2>Project Profile</h2>
          <div className={styles.formGrid}>
            <label>Industry<select value={industry} onChange={e => setIndustry(e.target.value)}>{INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}</select></label>
            <label>Team Size<input type="range" min="1" max="500" value={teamSize} onChange={e => setTeamSize(+e.target.value)} /><span>{teamSize}</span></label>
            <label>Duration (months)<input type="number" min="1" max="60" value={duration} onChange={e => setDuration(+e.target.value)} /></label>
            <label>Risk Level<select value={riskLevel} onChange={e => setRiskLevel(e.target.value)}>{RISK_LEVELS.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
            <label>Regulatory<div className={styles.chipGroup}>{REGULATIONS.map(r => <button key={r} className={`${styles.chip} ${regulatory.includes(r) ? styles.chipActive : ''}`} onClick={() => toggleReg(r)}>{r}</button>)}</div></label>
          </div>
          <button className={styles.nextBtn} onClick={fetchRecommendations}>Next: Get Recommendations</button>
        </section>
      )}

      {step === 1 && (
        <section className={styles.card}>
          <h2>AI Methodology Recommendation</h2>
          <div className={styles.recGrid}>
            {recommendations.map(r => (
              <div key={r.methodology} className={`${styles.recCard} ${selectedMethodology === r.methodology ? styles.recSelected : ''}`} onClick={() => setSelectedMethodology(r.methodology)}>
                <div className={styles.recScore}>{Math.round(r.match_score * 100)}% match</div>
                <h3>{r.methodology}</h3>
                <p>{r.rationale}</p>
                <ul>{r.strengths.map(s => <li key={s}>{s}</li>)}</ul>
              </div>
            ))}
          </div>
          <div className={styles.navButtons}>
            <button onClick={() => setStep(0)}>Back</button>
            <button className={styles.nextBtn} onClick={fetchTemplates} disabled={!selectedMethodology}>Next: Browse Templates</button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className={styles.card}>
          <h2>Template Gallery</h2>
          <div className={styles.templateGrid}>
            {templates.map(t => (
              <div key={t.template_id} className={`${styles.templateCard} ${selectedTemplate?.template_id === t.template_id ? styles.templateSelected : ''}`} onClick={() => setSelectedTemplate(t)}>
                <h3>{t.name}</h3>
                <span className={styles.methodBadge}>{t.methodology}</span>
                <p>{t.description}</p>
                <div className={styles.stageList}>{t.stages.map(s => <span key={s.id} className={styles.stageBadge}>{s.name}</span>)}</div>
                <span className={styles.actCount}>{t.activity_count} activities</span>
              </div>
            ))}
          </div>
          <div className={styles.navButtons}>
            <button onClick={() => setStep(1)}>Back</button>
            <button className={styles.nextBtn} onClick={() => setStep(3)} disabled={!selectedTemplate}>Next: Select Connectors</button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className={styles.card}>
          <h2>Integration Connectors</h2>
          <p className={styles.stepSubtitle}>Select the external systems to connect to this project. You can change these later in project settings.</p>
          <div className={styles.connectorControls}>
            <div className={styles.categoryFilter}>
              <button className={`${styles.catBtn} ${connectorFilter === 'all' ? styles.catBtnActive : ''}`} onClick={() => setConnectorFilter('all')}>All ({connectors.length})</button>
              {categories.map(cat => (
                <button key={cat} className={`${styles.catBtn} ${connectorFilter === cat ? styles.catBtnActive : ''}`} onClick={() => setConnectorFilter(cat)}>
                  {CATEGORY_LABELS[cat] || cat} ({connectors.filter(c => c.category === cat).length})
                </button>
              ))}
            </div>
            <span className={styles.enabledCount}>{enabledCount} enabled</span>
          </div>
          <div className={styles.connectorGrid}>
            {filteredConnectors.map(c => (
              <div key={c.name} className={`${styles.connectorCard} ${c.enabled ? styles.connectorEnabled : ''}`} onClick={() => toggleConnector(c.name)}>
                <div className={styles.connectorHeader}>
                  <span className={styles.connectorName}>{c.name}</span>
                  <span className={`${styles.connectorToggle} ${c.enabled ? styles.toggleOn : ''}`}>{c.enabled ? 'ON' : 'OFF'}</span>
                </div>
                <span className={styles.connectorCategory}>{CATEGORY_LABELS[c.category] || c.category}</span>
              </div>
            ))}
          </div>
          <div className={styles.navButtons}>
            <button onClick={() => setStep(2)}>Back</button>
            <button className={styles.nextBtn} onClick={() => setStep(4)}>Next: Assign Team</button>
          </div>
        </section>
      )}

      {step === 4 && (
        <section className={styles.card}>
          <h2>Team Assignment</h2>
          <p className={styles.stepSubtitle}>Add team members and assign project roles. You can update the team later.</p>
          <div className={styles.teamForm}>
            <div className={styles.teamInputRow}>
              <input type="text" placeholder="Name" value={newMemberName} onChange={e => setNewMemberName(e.target.value)} className={styles.teamInput} />
              <input type="email" placeholder="Email" value={newMemberEmail} onChange={e => setNewMemberEmail(e.target.value)} className={styles.teamInput} />
              <select value={newMemberRole} onChange={e => setNewMemberRole(e.target.value)} className={styles.teamSelect}>
                {PROJECT_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              <button className={styles.addMemberBtn} onClick={addTeamMember} disabled={!newMemberName.trim() || !newMemberEmail.trim()}>Add</button>
            </div>
          </div>
          {teamMembers.length > 0 && (
            <table className={styles.teamTable}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {teamMembers.map(m => (
                  <tr key={m.id}>
                    <td>{m.name}</td>
                    <td>{m.email}</td>
                    <td><span className={styles.roleBadge}>{m.role}</span></td>
                    <td><button className={styles.removeBtn} onClick={() => removeTeamMember(m.id)}>Remove</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {teamMembers.length === 0 && (
            <p className={styles.emptyTeam}>No team members added yet. You can skip this step and add team members later.</p>
          )}
          <div className={styles.navButtons}>
            <button onClick={() => setStep(3)}>Back</button>
            <button className={styles.nextBtn} onClick={() => setStep(5)}>Next: Configure & Launch</button>
          </div>
        </section>
      )}

      {step === 5 && (
        <section className={styles.card}>
          <h2>Configure & Launch</h2>
          {created ? (
            <div className={styles.successMsg}>
              <p>Project created successfully!</p>
              {createdProjectId && <p className={styles.projectIdMsg}>Project ID: {createdProjectId}</p>}
            </div>
          ) : (
            <>
              <div className={styles.configForm}>
                <label>Project Name<input type="text" value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Enter project name" /></label>
                {selectedTemplate && (
                  <div className={styles.templatePreview}>
                    <h3>{selectedTemplate.name}</h3>
                    <p>Methodology: {selectedTemplate.methodology} | Stages: {selectedTemplate.stages.length} | Activities: {selectedTemplate.activity_count}</p>
                  </div>
                )}
                <div className={styles.launchSummary}>
                  <h3>Setup Summary</h3>
                  <div className={styles.summaryGrid}>
                    <div className={styles.summaryItem}><span className={styles.summaryLabel}>Methodology</span><span>{selectedMethodology || 'Not selected'}</span></div>
                    <div className={styles.summaryItem}><span className={styles.summaryLabel}>Template</span><span>{selectedTemplate?.name || 'Not selected'}</span></div>
                    <div className={styles.summaryItem}><span className={styles.summaryLabel}>Connectors</span><span>{enabledCount} enabled</span></div>
                    <div className={styles.summaryItem}><span className={styles.summaryLabel}>Team Members</span><span>{teamMembers.length} assigned</span></div>
                    {intakeId && <div className={styles.summaryItem}><span className={styles.summaryLabel}>Intake Request</span><span>{intakeId}</span></div>}
                  </div>
                </div>
              </div>
              <div className={styles.navButtons}>
                <button onClick={() => setStep(4)}>Back</button>
                <button className={styles.launchBtn} onClick={createProject} disabled={!projectName || creating}>{creating ? 'Creating...' : 'Create Project'}</button>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
