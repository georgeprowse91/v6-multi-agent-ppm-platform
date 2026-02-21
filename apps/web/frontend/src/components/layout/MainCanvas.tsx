import { useLocation } from 'react-router-dom';
import { CanvasWorkspace } from '@/components/canvas';
import { MethodologyWorkspaceSurface } from '@/components/methodology';
import { useCanvasStore } from '@/store/useCanvasStore';
import styles from './MainCanvas.module.css';

interface MainCanvasProps {
  children: React.ReactNode;
}

export function MainCanvas({ children }: MainCanvasProps) {
  const { tabs } = useCanvasStore();
  const hasCanvasTabs = tabs.length > 0;
  const location = useLocation();
  const isProjectWorkspaceRoot = /^\/projects?\/[^/]+$/.test(location.pathname);

  return (
    <main className={styles.canvas} id="main-content" tabIndex={-1}>
      {hasCanvasTabs ? <CanvasWorkspace /> : (
        <div className={styles.content}>
          {isProjectWorkspaceRoot ? <MethodologyWorkspaceSurface /> : children}
        </div>
      )}
    </main>
  );
}
