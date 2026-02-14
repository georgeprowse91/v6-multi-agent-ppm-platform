import { Link } from 'react-router-dom';
import styles from './ForbiddenPage.module.css';

export function ForbiddenPage() {
  return (
    <div className={styles.page} role="alert" aria-live="assertive">
      <h1>403 · Access denied</h1>
      <p>You do not have permission to view this page or perform this action.</p>
      <Link to="/" className={styles.homeLink}>Return to home</Link>
    </div>
  );
}

export default ForbiddenPage;
