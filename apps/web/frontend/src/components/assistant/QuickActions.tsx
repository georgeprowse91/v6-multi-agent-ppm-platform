import { useEffect, useMemo, useRef, useState } from 'react';
import type { ActionChip } from '@/store/assistant';
import { ActionChipButton } from './ActionChipButton';
import styles from './QuickActions.module.css';

interface QuickActionsProps {
  chips: ActionChip[];
  onChipClick: (chip: ActionChip) => void;
}

const PRIORITY_ORDER: Record<ActionChip['priority'], number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export function QuickActions({ chips, onChipClick }: QuickActionsProps) {
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  const sortedChips = useMemo(
    () => [...chips].sort((a, b) => PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority]),
    [chips]
  );

  const visibleChips = sortedChips.slice(0, 3);
  const hiddenChips = sortedChips.slice(3);

  useEffect(() => {
    if (!showPopover) {
      return;
    }

    const handleOutsideClick = (event: MouseEvent) => {
      if (!popoverRef.current?.contains(event.target as Node)) {
        setShowPopover(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [showPopover]);

  if (sortedChips.length === 0) {
    return null;
  }

  return (
    <div className={styles.bar}>
      {showPopover && hiddenChips.length > 0 && (
        <div className={styles.popover} ref={popoverRef}>
          <div className={styles.popoverList}>
            {sortedChips.map((chip) => (
              <ActionChipButton
                key={chip.id}
                chip={chip}
                onClick={() => {
                  onChipClick(chip);
                  setShowPopover(false);
                }}
                small
              />
            ))}
          </div>
        </div>
      )}

      <div className={styles.chipsRow}>
        {visibleChips.map((chip) => (
          <ActionChipButton
            key={chip.id}
            chip={chip}
            onClick={() => onChipClick(chip)}
            small
          />
        ))}

        {hiddenChips.length > 0 && (
          <button
            type="button"
            className={styles.morePill}
            onClick={() => setShowPopover((prev) => !prev)}
            aria-expanded={showPopover}
            aria-label={`Show ${hiddenChips.length} more quick actions`}
          >
            +{hiddenChips.length} more
          </button>
        )}
      </div>
    </div>
  );
}
