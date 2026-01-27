import { CanvasWorkspace } from '@/components/canvas';
import { useCanvasStore } from '@/store/useCanvasStore';
import styles from './MainCanvas.module.css';

interface MainCanvasProps {
  children: React.ReactNode;
}

export function MainCanvas({ children }: MainCanvasProps) {
  const { tabs } = useCanvasStore();
  const hasCanvasTabs = tabs.length > 0;

  return (
    <main className={styles.canvas}>
      {hasCanvasTabs ? (
        <CanvasWorkspace />
      ) : (
        <div className={styles.content}>{children}</div>
      )}
    </main>
  );
}
