import { Icon } from '@/components/icon/Icon';
import {
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  type ActionChip,
} from '@/store/assistant';
import styles from './ActionChipButton.module.css';

interface ActionChipButtonProps {
  chip: ActionChip;
  onClick: () => void;
  small?: boolean;
}

export function ActionChipButton({ chip, onClick, small = false }: ActionChipButtonProps) {
  const colors = CATEGORY_COLORS[chip.category];
  const icon = chip.icon ?? CATEGORY_ICONS[chip.category];

  return (
    <button
      className={`${styles.chip} ${small ? styles.chipSmall : ''} ${!chip.enabled ? styles.chipDisabled : ''}`}
      onClick={onClick}
      disabled={!chip.enabled}
      title={chip.description}
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      }}
    >
      <Icon semantic={icon} decorative className={styles.chipIcon} size={small ? 'sm' : 'md'} />
      <span className={styles.chipLabel}>{chip.label}</span>
    </button>
  );
}
