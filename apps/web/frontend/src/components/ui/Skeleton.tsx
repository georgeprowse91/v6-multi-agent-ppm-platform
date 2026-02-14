import type { CSSProperties } from 'react';
import styles from './Skeleton.module.css';

type SkeletonVariant = 'text' | 'card' | 'circle' | 'chart';

interface SkeletonProps {
  variant?: SkeletonVariant;
  className?: string;
  width?: CSSProperties['width'];
  height?: CSSProperties['height'];
}

export function Skeleton({
  variant = 'text',
  className,
  width,
  height,
}: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`${styles.skeleton} ${styles[variant]} ${className ?? ''}`.trim()}
      style={{ width, height }}
    />
  );
}
