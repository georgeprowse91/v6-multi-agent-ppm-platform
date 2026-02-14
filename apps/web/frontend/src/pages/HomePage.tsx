import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { OnboardingTour } from '@/components/onboarding/OnboardingTour';
import { ENTRY_ASSISTANT_CHIPS } from '@/components/assistant/entryQuickActions';
import { useAssistantStore } from '@/store/assistant';
import styles from './HomePage.module.css';

export function HomePage() {
  const navigate = useNavigate();
  const { setActionChips, addAssistantMessage } = useAssistantStore();

  useEffect(() => {
    setActionChips(ENTRY_ASSISTANT_CHIPS);
    addAssistantMessage(
      'Welcome. Choose a quick action to log intake or open a portfolio, program, or project workspace.',
      ENTRY_ASSISTANT_CHIPS
    );
  }, [addAssistantMessage, setActionChips]);

  return (
    <div className={styles.page}>
      <OnboardingTour />
      <section className={styles.entryCard}>
        <h1>Welcome to the PPM Platform</h1>
        <p>
          Start from assistant quick actions, or launch a fresh intake flow.
        </p>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => navigate('/intake/new', { state: { resetAt: Date.now() } })}
        >
          Log new intake
        </button>
      </section>
    </div>
  );
}

export default HomePage;
