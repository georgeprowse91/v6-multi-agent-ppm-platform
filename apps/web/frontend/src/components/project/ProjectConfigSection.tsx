import React, { useState } from 'react';
import { AgentGallery } from './AgentGallery';
import { ProjectConnectorGallery } from './ProjectConnectorGallery';
import styles from './ProjectConfigSection.module.css';

interface ProjectConfigSectionProps {
  projectId: string;
}

type ProjectConfigTab = 'agents' | 'connectors';

export function ProjectConfigSection({ projectId }: ProjectConfigSectionProps) {
  const [activeTab, setActiveTab] = useState<ProjectConfigTab>('agents');

  return (
    <section className={styles.container}>
      <div className={styles.tabList} role="tablist" aria-label="Project configuration tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'agents'}
          className={`${styles.tabButton} ${activeTab === 'agents' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('agents')}
        >
          Agent Gallery
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'connectors'}
          className={`${styles.tabButton} ${activeTab === 'connectors' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('connectors')}
        >
          Connector Gallery
        </button>
      </div>

      <div className={styles.tabPanel} role="tabpanel">
        {activeTab === 'agents' ? (
          <AgentGallery projectId={projectId} />
        ) : (
          <ProjectConnectorGallery projectId={projectId} />
        )}
      </div>
    </section>
  );
}

export default ProjectConfigSection;
