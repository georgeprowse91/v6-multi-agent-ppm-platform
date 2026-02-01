import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Shepherd from 'shepherd.js';
import { useAppStore } from '@/store';
import styles from './TourProvider.module.css';

interface TourContextValue {
  startTour: () => void;
  openOnboarding: () => void;
}

const TourContext = createContext<TourContextValue | undefined>(undefined);

const TOUR_VERSION = '2024-10-connector-certifications';
const TOUR_STORAGE_KEY = 'ppm-tour-version';
const TOUR_DISMISSED_KEY = 'ppm-tour-dismissed';

const waitForElement = (selector: string, timeout = 2500) =>
  new Promise<void>((resolve) => {
    const start = Date.now();
    const check = () => {
      if (document.querySelector(selector)) {
        resolve();
        return;
      }
      if (Date.now() - start >= timeout) {
        resolve();
        return;
      }
      requestAnimationFrame(check);
    };
    check();
  });

export function TourProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAppStore();
  const navigate = useNavigate();
  const tourRef = useRef<Shepherd.Tour | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const markSeen = useCallback(() => {
    localStorage.setItem(TOUR_STORAGE_KEY, TOUR_VERSION);
    localStorage.removeItem(TOUR_DISMISSED_KEY);
  }, []);

  const markDismissed = useCallback(() => {
    localStorage.setItem(TOUR_DISMISSED_KEY, TOUR_VERSION);
  }, []);

  const ensureTour = useCallback(() => {
    if (tourRef.current) return tourRef.current;
    const tour = new Shepherd.Tour({
      defaultStepOptions: {
        cancelIcon: { enabled: true },
        scrollTo: { behavior: 'smooth', block: 'center' },
      },
    });

    tour.addStep({
      id: 'welcome',
      text: 'Welcome! Let’s tour the expanded web console capabilities.',
      buttons: [{ text: 'Next', action: tour.next }],
    });

    tour.addStep({
      id: 'connectors-nav',
      text: 'Use the Connectors navigation to configure integrations and evidence.',
      attachTo: { element: '[data-tour="nav-connectors"]', on: 'right' },
      buttons: [
        { text: 'Back', action: tour.back },
        { text: 'Next', action: tour.next },
      ],
    });

    tour.addStep({
      id: 'connector-gallery',
      text: 'Track connector certification status and upload evidence here.',
      attachTo: { element: '[data-tour="connector-gallery"]', on: 'top' },
      beforeShowPromise: async () => {
        navigate('/marketplace/connectors');
        await waitForElement('[data-tour="connector-gallery"]');
      },
      buttons: [
        { text: 'Back', action: tour.back },
        { text: 'Next', action: tour.next },
      ],
    });

    tour.addStep({
      id: 'agents-nav',
      text: 'Manage orchestration agents and their configurations.',
      attachTo: { element: '[data-tour="nav-agents"]', on: 'right' },
      beforeShowPromise: async () => {
        navigate('/config/agents');
        await waitForElement('[data-tour="nav-agents"]');
      },
      buttons: [
        { text: 'Back', action: tour.back },
        { text: 'Next', action: tour.next },
      ],
    });

    tour.addStep({
      id: 'workflow-monitor',
      text: 'Monitor workflow performance and analytics from Workflow Monitor.',
      attachTo: { element: '[data-tour="nav-workflow-monitor"]', on: 'right' },
      beforeShowPromise: async () => {
        navigate('/workflows/monitoring');
        await waitForElement('[data-tour="nav-workflow-monitor"]');
      },
      buttons: [
        { text: 'Back', action: tour.back },
        { text: 'Next', action: tour.next },
      ],
    });

    tour.addStep({
      id: 'assistant-panel',
      text: 'Use the Assistant panel for contextual guidance and quick actions.',
      attachTo: { element: '[data-tour="assistant-panel"]', on: 'left' },
      buttons: [
        { text: 'Back', action: tour.back },
        { text: 'Finish', action: tour.complete },
      ],
    });

    tour.on('complete', markSeen);
    tour.on('cancel', markDismissed);
    tourRef.current = tour;
    return tour;
  }, [markDismissed, markSeen, navigate]);

  const startTour = useCallback(() => {
    setShowOnboarding(false);
    const tour = ensureTour();
    tour.start();
  }, [ensureTour]);

  const openOnboarding = useCallback(() => {
    setShowOnboarding(true);
  }, []);

  useEffect(() => {
    if (session.loading) return;
    const seenVersion = localStorage.getItem(TOUR_STORAGE_KEY);
    const dismissedVersion = localStorage.getItem(TOUR_DISMISSED_KEY);
    if (seenVersion !== TOUR_VERSION && dismissedVersion !== TOUR_VERSION) {
      setShowOnboarding(true);
    }
  }, [session.loading]);

  const value = useMemo(() => ({ startTour, openOnboarding }), [openOnboarding, startTour]);

  return (
    <TourContext.Provider value={value}>
      {children}
      {showOnboarding && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modal}>
            <h2>Welcome to the expanded web console</h2>
            <p>
              We&apos;ve added connector certification evidence tracking and guided walkthroughs
              for the latest UI updates. Start a quick tour to see what&apos;s new.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.secondaryButton}
                onClick={() => {
                  setShowOnboarding(false);
                  markDismissed();
                }}
              >
                Maybe later
              </button>
              <button className={styles.primaryButton} onClick={startTour}>
                Start walkthrough
              </button>
            </div>
          </div>
        </div>
      )}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) {
    throw new Error('useTour must be used within a TourProvider');
  }
  return context;
}
