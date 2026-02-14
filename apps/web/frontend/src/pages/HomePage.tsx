import { useNavigate } from 'react-router-dom';
import { ENTRY_ASSISTANT_CHIPS } from '@/components/assistant/entryQuickActions';
import { OnboardingTour } from '@/components/onboarding/OnboardingTour';
import styles from './HomePage.module.css';

const routeByChipId: Record<string, string> = {
  'entry-log-intake': '/intake/new',
  'entry-open-portfolio': '/portfolios',
  'entry-open-program': '/programs',
  'entry-open-project': '/projects',
};

export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <OnboardingTour />
      <section className={styles.entryCard}>
        <h1>Welcome to the PPM Platform</h1>
        <p>Choose where to start. The assistant panel is already loaded and offers matching quick-action chips.</p>
        <div className={styles.chipRow} aria-label="Assistant chips">
          {ENTRY_ASSISTANT_CHIPS.map((chip) => (
            <span key={chip.id} className={styles.chip}>{chip.label}</span>
          ))}
        </div>
        <div className={styles.buttonGrid}>
          {ENTRY_ASSISTANT_CHIPS.map((chip) => (
            <button
              key={`button-${chip.id}`}
              type="button"
              className={styles.primaryButton}
              onClick={() => navigate(routeByChipId[chip.id])}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

export default HomePage;
