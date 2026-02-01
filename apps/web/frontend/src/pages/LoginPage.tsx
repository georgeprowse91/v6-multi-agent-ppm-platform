import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import styles from './LoginPage.module.css';

const errorMessages: Record<string, string> = {
  invalid_credentials: 'Invalid username or password.',
  access_denied: 'Access denied. Please try again or contact support.',
};

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const errorParam = params.get('error');
    if (errorParam) {
      setError(errorMessages[errorParam] ?? 'Unable to sign in. Please try again.');
    }
  }, [location.search]);

  useEffect(() => {
    let mounted = true;
    const checkSession = async () => {
      try {
        const response = await fetch('/session');
        if (!response.ok) return;
        const data = await response.json();
        if (!mounted) return;
        if (data.authenticated) {
          navigate('/', { replace: true });
        }
      } catch {
        // Ignore session errors and allow the user to attempt login.
      }
    };
    checkSession();
    return () => {
      mounted = false;
    };
  }, [navigate]);

  const startOidcFlow = async () => {
    setSubmitting(true);
    try {
      const response = await fetch('/login?return_to=/', { method: 'GET', redirect: 'manual' });
      if (response.status >= 400) {
        setError(
          response.status === 401 || response.status === 403
            ? 'Invalid username or password.'
            : 'Unable to start sign-in. Please try again.'
        );
        return;
      }
      const redirectUrl = response.headers.get('Location');
      window.location.assign(redirectUrl ?? '/login?return_to=/');
    } catch {
      setError('Unable to start sign-in. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!username.trim() || !password.trim()) {
      setError('Invalid username or password.');
      return;
    }
    await startOidcFlow();
  };

  const handleSso = async () => {
    setError(null);
    await startOidcFlow();
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <span className={styles.logo}>PPM Platform</span>
          <h1 className={styles.title}>Sign in</h1>
          <p className={styles.subtitle}>Access your projects and workflows securely.</p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label} htmlFor="username">
            Username
          </label>
          <input
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            className={styles.input}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            aria-invalid={Boolean(error)}
          />

          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className={styles.input}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={Boolean(error)}
          />

          {error ? <p className={styles.error}>{error}</p> : null}

          <button className={styles.primaryButton} type="submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <button className={styles.secondaryButton} type="button" onClick={handleSso} disabled={submitting}>
          Sign in with SSO
        </button>

        <div className={styles.footer}>
          <Link to="/reset-password" className={styles.resetLink}>
            Reset password
          </Link>
        </div>
      </div>
    </div>
  );
}
