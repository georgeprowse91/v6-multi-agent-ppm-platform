import { useNavigate } from 'react-router-dom';
import { OnboardingTour } from '@/components/onboarding/OnboardingTour';
import styles from './HomePage.module.css';

export function HomePage() {
  const navigate = useNavigate();

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
