import { useCallback, useEffect, useState } from 'react';
import { requestJson } from '@/services/apiClient';
import styles from './ExecutiveBriefingPage.module.css';

interface BriefingResponse {
  briefing_id: string;
  title: string;
  generated_at: string;
  audience: string;
  content: string;
  sections: Array<{ title: string; content: string }>;
  metadata?: Record<string, unknown>;
}

interface BriefingExportResponse {
  briefing_id: string;
  export_format: string;
  filename: string;
  content_base64: string;
  content_type: string;
}

interface BriefingSchedule {
  schedule_id: string;
  portfolio_id: string;
  audience: string;
  frequency: string;
  recipients: string[];
  channels: string[];
  export_format: string;
  enabled: boolean;
  created_at: string;
}

const AUDIENCES = [
  { value: 'board', label: 'Board of Directors' },
  { value: 'c_suite', label: 'C-Suite Executive' },
  { value: 'pmo', label: 'PMO Leadership' },
  { value: 'delivery_team', label: 'Delivery Team' },
];

const SECTIONS = ['highlights', 'risks', 'financials', 'schedule', 'resources', 'recommendations'];

const FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'fortnightly', label: 'Fortnightly' },
  { value: 'monthly', label: 'Monthly' },
];

const CHANNELS = [
  { value: 'email', label: 'Email' },
  { value: 'teams', label: 'Microsoft Teams' },
  { value: 'slack', label: 'Slack' },
];

export default function ExecutiveBriefingPage() {
  const [audience, setAudience] = useState('c_suite');
  const [tone, setTone] = useState('formal');
  const [selectedSections, setSelectedSections] = useState<string[]>(SECTIONS);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Schedule config
  const [showSchedulePanel, setShowSchedulePanel] = useState(false);
  const [scheduleFrequency, setScheduleFrequency] = useState('weekly');
  const [scheduleRecipients, setScheduleRecipients] = useState('');
  const [scheduleChannels, setScheduleChannels] = useState<string[]>(['email']);
  const [scheduleExportFormat, setScheduleExportFormat] = useState('pdf');
  const [schedules, setSchedules] = useState<BriefingSchedule[]>([]);
  const [savingSchedule, setSavingSchedule] = useState(false);

  const toggleSection = (s: string) => {
    setSelectedSections(prev =>
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
    );
  };

  const toggleChannel = (ch: string) => {
    setScheduleChannels(prev =>
      prev.includes(ch) ? prev.filter(x => x !== ch) : [...prev, ch]
    );
  };

  const generate = useCallback(async () => {
    setGenerating(true);
    try {
      const result = await requestJson<BriefingResponse>('/api/briefings/generate', {
        method: 'POST',
        body: JSON.stringify({
          portfolio_id: 'default',
          audience,
          tone,
          sections: selectedSections,
          format: 'markdown',
        }),
      });
      setBriefing(result);
    } catch {
      // demo fallback
    } finally {
      setGenerating(false);
    }
  }, [audience, tone, selectedSections]);

  const copyToClipboard = () => {
    if (briefing) navigator.clipboard.writeText(briefing.content);
  };

  const exportBriefing = async (format: 'pdf' | 'pptx') => {
    if (!briefing) return;
    setExporting(true);
    try {
      const result = await requestJson<BriefingExportResponse>('/api/briefings/export', {
        method: 'POST',
        body: JSON.stringify({
          briefing_id: briefing.briefing_id,
          export_format: format,
        }),
      });
      // Trigger browser download
      const byteString = atob(result.content_base64);
      const bytes = new Uint8Array(byteString.length);
      for (let i = 0; i < byteString.length; i++) {
        bytes[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: result.content_type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = result.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      // export unavailable
    } finally {
      setExporting(false);
    }
  };

  const loadSchedules = useCallback(async () => {
    try {
      const result = await requestJson<BriefingSchedule[]>('/api/briefings/schedules');
      setSchedules(result);
    } catch {
      // schedules unavailable
    }
  }, []);

  const saveSchedule = async () => {
    const recipients = scheduleRecipients
      .split(',')
      .map(r => r.trim())
      .filter(Boolean);
    if (recipients.length === 0 || scheduleChannels.length === 0) return;

    setSavingSchedule(true);
    try {
      await requestJson<BriefingSchedule>('/api/briefings/schedule', {
        method: 'POST',
        body: JSON.stringify({
          portfolio_id: 'default',
          audience,
          tone,
          sections: selectedSections,
          frequency: scheduleFrequency,
          recipients,
          channels: scheduleChannels,
          export_format: scheduleExportFormat,
          enabled: true,
        }),
      });
      setScheduleRecipients('');
      await loadSchedules();
    } catch {
      // schedule creation unavailable
    } finally {
      setSavingSchedule(false);
    }
  };

  const deleteSchedule = async (scheduleId: string) => {
    try {
      await requestJson(`/api/briefings/schedules/${scheduleId}`, {
        method: 'DELETE',
      });
      await loadSchedules();
    } catch {
      // delete unavailable
    }
  };

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Executive Briefing Generator</h1>
      </header>

      <div className={styles.layout}>
        {/* Config Panel */}
        <aside className={styles.configPanel}>
          <div className={styles.configSection}>
            <label>Audience</label>
            <select value={audience} onChange={e => setAudience(e.target.value)}>
              {AUDIENCES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
          </div>

          <div className={styles.configSection}>
            <label>Tone</label>
            <div className={styles.radioGroup}>
              {['formal', 'concise', 'detailed'].map(t => (
                <label key={t} className={styles.radioLabel}>
                  <input type="radio" name="tone" value={t} checked={tone === t} onChange={() => setTone(t)} />
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </label>
              ))}
            </div>
          </div>

          <div className={styles.configSection}>
            <label>Sections</label>
            <div className={styles.checkboxGroup}>
              {SECTIONS.map(s => (
                <label key={s} className={styles.checkboxLabel}>
                  <input type="checkbox" checked={selectedSections.includes(s)} onChange={() => toggleSection(s)} />
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </label>
              ))}
            </div>
          </div>

          <button className={styles.generateBtn} onClick={generate} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Briefing'}
          </button>

          <div className={styles.divider} />

          <button
            className={styles.scheduleToggleBtn}
            onClick={() => setShowSchedulePanel(!showSchedulePanel)}
          >
            {showSchedulePanel ? 'Hide Schedule Settings' : 'Schedule Delivery'}
          </button>

          {showSchedulePanel && (
            <div className={styles.schedulePanel}>
              <div className={styles.configSection}>
                <label>Frequency</label>
                <select value={scheduleFrequency} onChange={e => setScheduleFrequency(e.target.value)}>
                  {FREQUENCIES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
              </div>

              <div className={styles.configSection}>
                <label>Recipients (comma-separated emails)</label>
                <input
                  type="text"
                  className={styles.textInput}
                  placeholder="ceo@company.com, cfo@company.com"
                  value={scheduleRecipients}
                  onChange={e => setScheduleRecipients(e.target.value)}
                />
              </div>

              <div className={styles.configSection}>
                <label>Delivery Channels</label>
                <div className={styles.checkboxGroup}>
                  {CHANNELS.map(ch => (
                    <label key={ch.value} className={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        checked={scheduleChannels.includes(ch.value)}
                        onChange={() => toggleChannel(ch.value)}
                      />
                      {ch.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className={styles.configSection}>
                <label>Export Format</label>
                <div className={styles.radioGroup}>
                  {['pdf', 'pptx'].map(fmt => (
                    <label key={fmt} className={styles.radioLabel}>
                      <input
                        type="radio"
                        name="exportFormat"
                        value={fmt}
                        checked={scheduleExportFormat === fmt}
                        onChange={() => setScheduleExportFormat(fmt)}
                      />
                      {fmt.toUpperCase()}
                    </label>
                  ))}
                </div>
              </div>

              <button
                className={styles.generateBtn}
                onClick={saveSchedule}
                disabled={savingSchedule || !scheduleRecipients.trim()}
              >
                {savingSchedule ? 'Saving...' : 'Save Schedule'}
              </button>
            </div>
          )}

          {schedules.length > 0 && (
            <div className={styles.schedulesListSection}>
              <label>Active Schedules</label>
              {schedules.map(s => (
                <div key={s.schedule_id} className={styles.scheduleCard}>
                  <div className={styles.scheduleCardHeader}>
                    <span className={styles.scheduleFrequency}>{s.frequency}</span>
                    <button
                      className={styles.deleteScheduleBtn}
                      onClick={() => deleteSchedule(s.schedule_id)}
                      title="Delete schedule"
                    >
                      Remove
                    </button>
                  </div>
                  <div className={styles.scheduleCardDetail}>
                    {s.recipients.length} recipient{s.recipients.length !== 1 ? 's' : ''} via {s.channels.join(', ')} ({s.export_format.toUpperCase()})
                  </div>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* Preview */}
        <main className={styles.previewPanel}>
          {briefing ? (
            <>
              <div className={styles.previewHeader}>
                <h2>{briefing.title}</h2>
                <div className={styles.previewActions}>
                  <button onClick={copyToClipboard}>Copy</button>
                  <button onClick={generate}>Regenerate</button>
                  <button onClick={() => exportBriefing('pdf')} disabled={exporting}>
                    {exporting ? 'Exporting...' : 'PDF'}
                  </button>
                  <button onClick={() => exportBriefing('pptx')} disabled={exporting}>
                    PPTX
                  </button>
                </div>
              </div>
              {briefing.metadata?.cross_agent_sources && (
                <div className={styles.dataSources}>
                  Data sources: {(briefing.metadata.cross_agent_sources as string[]).join(', ')}
                </div>
              )}
              <div className={styles.previewContent}>
                <pre>{briefing.content}</pre>
              </div>
            </>
          ) : (
            <div className={styles.emptyState}>
              <p>Configure your briefing parameters and click "Generate Briefing" to create an AI-powered executive summary with cross-agent intelligence.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
