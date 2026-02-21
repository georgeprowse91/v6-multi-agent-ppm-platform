import { useEffect } from 'react';
import { Header } from './Header';
import { LeftPanel } from './LeftPanel';
import { MainCanvas } from './MainCanvas';
import { AssistantPanel } from '@/components/assistant';
import { TourProvider } from '@/components/tours';
import { useAppStore } from '@/store';
import { useRealtimeConsole } from '@/hooks/useRealtimeConsole';
import styles from './AppLayout.module.css';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { setFeatureFlags } = useAppStore();
  useRealtimeConsole();

  useEffect(() => {
    let mounted = true;
    const loadConfig = async () => {
      try {
        const response = await fetch('/v1/config');
        if (!response.ok) {
          throw new Error('Unable to load config');
        }
        const data = await response.json();
        if (!mounted) return;
        setFeatureFlags(data.feature_flags ?? {});
      } catch {
        if (!mounted) return;
        setFeatureFlags({});
      }
    };
    loadConfig();
    return () => {
      mounted = false;
    };
  }, [setFeatureFlags]);

  return (
    <TourProvider>
      <div className={styles.layout}>
        <a href="#main-content" className={styles.skipLink}>Skip to main content</a>
        <Header />
        <div className={styles.body}>
          <LeftPanel />
          <MainCanvas>{children}</MainCanvas>
          <AssistantPanel />
        </div>
      </div>
    </TourProvider>
  );
}
