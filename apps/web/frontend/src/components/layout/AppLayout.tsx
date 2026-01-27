import { Header } from './Header';
import { LeftPanel } from './LeftPanel';
import { MainCanvas } from './MainCanvas';
import { AssistantPanel } from '@/components/assistant';
import styles from './AppLayout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className={styles.layout}>
      <Header />
      <div className={styles.body}>
        <LeftPanel />
        <MainCanvas>{children}</MainCanvas>
        <AssistantPanel />
      </div>
    </div>
  );
}
