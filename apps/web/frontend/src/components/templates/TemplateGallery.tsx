import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMethodologyStore } from '@/store/methodology';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useAgentConfigStore } from '@/store/agentConfig';
import { useConnectorStore } from '@/store/connectors';
import { useAppStore } from '@/store';
import { canManageConfig } from '@/auth/permissions';
import { createArtifact, createEmptyContent, type CanvasType } from '@ppm/canvas-engine';
import type { MethodologyMap } from '@/store/methodology';
import { Icon } from '@/components/icon/Icon';
import styles from './TemplateGallery.module.css';

type TemplateTab = {
  activity_id?: string | null;
  type: CanvasType;
  title: string;
};

type TemplateSummary = {
  id: string;
  name: string;
  version: string;
  available_versions: string[];
  summary: string;
  description: string;
  methodology_name: string;
  methodology_type: string;
};

type TemplateDefinition = {
  id: string;
  name: string;
  version: string;
  available_versions: string[];
  summary: string;
  description: string;
  methodology: MethodologyMap;
  agent_config: { enabled: string[]; disabled: string[] };
  connector_config: { enabled: string[]; disabled: string[] };
  initial_tabs: TemplateTab[];
  dashboards: TemplateTab[];
};

type TemplateApplyResponse = {
  project: {
    id: string;
    name: string;
  };
  template: TemplateDefinition;
};

function attachArtifactIds(
  methodology: MethodologyMap,
  artifactMap: Record<string, string>
): MethodologyMap {
  return {
    ...methodology,
    stages: methodology.stages.map((stage) => ({
      ...stage,
      activities: stage.activities.map((activity) => {
        const artifactId = artifactMap[activity.id];
        return artifactId ? { ...activity, artifactId } : activity;
      }),
    })),
  };
}

export function TemplateGallery() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projectNames, setProjectNames] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState<Record<string, boolean>>({});
  const [selectedVersions, setSelectedVersions] = useState<Record<string, string>>({});

  const { loadProjectMethodology } = useMethodologyStore();
  const { openArtifact } = useCanvasStore();
  const { fetchAgents, applyTemplateAgents } = useAgentConfigStore();
  const { fetchConnectors, applyTemplateConnectors } = useConnectorStore();
  const { session } = useAppStore();
  const canApply = canManageConfig(session.user?.permissions);

  useEffect(() => {
    const loadTemplates = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/templates');
        if (!response.ok) {
          throw new Error(`Failed to fetch templates: ${response.statusText}`);
        }
        const data: TemplateSummary[] = await response.json();
        setTemplates(data);
        setProjectNames(
          data.reduce<Record<string, string>>((acc, template) => {
            acc[template.id] = `${template.name} Project`;
            return acc;
          }, {})
        );
        setSelectedVersions(
          data.reduce<Record<string, string>>((acc, template) => {
            acc[template.id] = template.version;
            return acc;
          }, {})
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    loadTemplates();
    fetchAgents();
    fetchConnectors();
  }, [fetchAgents, fetchConnectors]);

  const templateCards = useMemo(() => templates, [templates]);

  const handleNameChange = (templateId: string, value: string) => {
    setProjectNames((prev) => ({ ...prev, [templateId]: value }));
  };

  const handleVersionChange = (templateId: string, value: string) => {
    setSelectedVersions((prev) => ({ ...prev, [templateId]: value }));
  };

  const handleApplyTemplate = async (templateId: string) => {
    if (!canApply) {
      setError('You do not have permission to apply templates.');
      return;
    }
    const projectName = projectNames[templateId]?.trim();
    if (!projectName) {
      setError('Please provide a project name before applying a template.');
      return;
    }

    setApplying((prev) => ({ ...prev, [templateId]: true }));
    setError(null);

    try {
      const response = await fetch(`/api/templates/${templateId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: projectName,
          version: selectedVersions[templateId],
        }),
      });
      if (!response.ok) {
        throw new Error(`Failed to apply template: ${response.statusText}`);
      }

      const data: TemplateApplyResponse = await response.json();
      const { project, template } = data;

      applyTemplateAgents(project.id, template.agent_config);
      applyTemplateConnectors(template.connector_config);

      const artifactMap: Record<string, string> = {};
      const tabs = [...template.initial_tabs, ...template.dashboards];
      tabs.forEach((tab) => {
        const artifact = createArtifact(
          tab.type,
          tab.title,
          project.id,
          createEmptyContent(tab.type)
        );
        if (tab.activity_id) {
          artifactMap[tab.activity_id] = artifact.id;
        }
        openArtifact(artifact);
      });

      const updatedMethodology = attachArtifactIds(template.methodology, artifactMap);
      loadProjectMethodology({
        projectId: project.id,
        projectName: project.name,
        methodology: updatedMethodology,
        currentActivityId: null,
        expandedStageIds: [updatedMethodology.stages[0]?.id].filter(Boolean),
      });

      navigate(`/project/${project.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setApplying((prev) => ({ ...prev, [templateId]: false }));
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading templates...</div>
      </div>
    );
  }

  if (error && templates.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <p>Error loading templates: {error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Templates Gallery</h1>
          <p className={styles.subtitle}>
            Choose a template to bootstrap a project with the right methodology, agents, connectors,
            and starter artifacts.
          </p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.count}>{templates.length} templates</span>
        </div>
      </header>

      {error && (
        <div className={styles.inlineError}>
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">
            <Icon semantic="actions.cancelDismiss" label="Dismiss error" />
          </button>
        </div>
      )}

      <div className={styles.grid}>
        {templateCards.map((template) => (
          <article key={template.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>{template.name}</h2>
                <p className={styles.cardSummary}>{template.summary}</p>
              </div>
              <span className={styles.version}>v{template.version}</span>
            </div>
            <p className={styles.cardDescription}>{template.description}</p>
            <div className={styles.metaRow}>
              <span className={styles.badge}>{template.methodology_name}</span>
              <span className={styles.badgeSecondary}>{template.methodology_type}</span>
              <span className={styles.badgeSecondary}>
                Versions: {template.available_versions.join(', ')}
              </span>
            </div>

            <label className={styles.inputLabel}>
              Template version
              <select
                className={styles.select}
                value={selectedVersions[template.id] ?? template.version}
                onChange={(e) => handleVersionChange(template.id, e.target.value)}
              >
                {template.available_versions.map((version) => (
                  <option key={version} value={version}>
                    v{version}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.inputLabel}>
              Project name
              <input
                className={styles.input}
                value={projectNames[template.id] || ''}
                onChange={(e) => handleNameChange(template.id, e.target.value)}
                placeholder="New project name"
              />
            </label>

            <button
              className={styles.applyButton}
              onClick={() => handleApplyTemplate(template.id)}
              disabled={Boolean(applying[template.id]) || !canApply}
              aria-disabled={!canApply}
              title={canApply ? 'Apply template' : 'Read-only'}
            >
              {applying[template.id] ? 'Applying...' : 'Use This Template'}
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
