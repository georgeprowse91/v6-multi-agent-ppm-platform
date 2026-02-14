import type { CSSProperties, ReactNode } from 'react';
import styles from './FadeIn.module.css';

interface FadeInProps {
  children: ReactNode;
  className?: string;
  delayMs?: number;
}

export function FadeIn({ children, className, delayMs = 0 }: FadeInProps) {
  const fadeStyle = {
    '--fade-in-delay': `${delayMs}ms`,
  } as CSSProperties;

  return (
    <div className={[styles.fadeIn, className].filter(Boolean).join(' ')} style={fadeStyle}>
      {children}
    </div>
  );
}
