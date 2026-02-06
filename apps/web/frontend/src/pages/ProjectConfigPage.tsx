import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { ProjectConfigSection } from '@/components/project';

type ProjectConfigTab = 'agents' | 'connectors';

const VALID_TABS: ProjectConfigTab[] = ['agents', 'connectors'];

export function ProjectConfigPage() {
  const { projectId, tab } = useParams();

  const defaultTab = useMemo<ProjectConfigTab>(() => {
    if (tab && VALID_TABS.includes(tab as ProjectConfigTab)) {
      return tab as ProjectConfigTab;
    }
    return 'agents';
  }, [tab]);

  if (!projectId) {
    return null;
  }

  return (
    <ProjectConfigSection projectId={projectId} defaultTab={defaultTab} />
  );
}
