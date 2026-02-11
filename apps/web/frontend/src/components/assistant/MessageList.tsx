import { useEffect, useMemo, useRef, type ReactNode } from 'react';
import { Icon } from '@/components/icon/Icon';
import {
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  type AIState,
  type ActionChip,
  type AssistantContext,
  type AssistantMessage,
} from '@/store/assistant';
import styles from './MessageList.module.css';
import bubbleStyles from './MessageBubble.module.css';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  messages: AssistantMessage[];
  aiState: AIState;
  context: AssistantContext | null;
  onChipClick: (chip: ActionChip) => void;
  renderActionChip?: (chip: ActionChip, options?: { small?: boolean }) => ReactNode;
}

const typingStateLabels: Record<'thinking' | 'tool_use' | 'streaming', string> = {
  thinking: 'Thinking…',
  tool_use: 'Working…',
  streaming: 'Responding…',
};

export function MessageList({
  messages,
  aiState,
  context,
  onChipClick,
  renderActionChip,
}: MessageListProps) {
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, aiState]);

  const quickStartChips = useMemo<ActionChip[]>(() => {
    if (!context?.currentActivityId) {
      return [
        {
          id: 'quick-start-first-activity',
          label: 'Start first activity',
          category: 'navigate',
          priority: 'high',
          actionType: 'custom',
          payload: { type: 'custom', actionKey: 'start_first_activity' },
          enabled: true,
          description: 'Jump into your first project activity.',
        },
        {
          id: 'quick-start-dashboard',
          label: 'View Dashboard',
          category: 'navigate',
          priority: 'medium',
          actionType: 'open_dashboard',
          payload: { type: 'open_dashboard' },
          enabled: true,
          description: 'Open the project dashboard.',
        },
        {
          id: 'quick-start-question',
          label: 'Ask a question',
          category: 'review',
          priority: 'medium',
          actionType: 'custom',
          payload: { type: 'custom', actionKey: 'ask_question' },
          enabled: true,
          description: 'Start by asking the assistant a question.',
        },
      ];
    }

    return [
      {
        id: 'quick-activity-open',
        label: `Open ${context.currentActivityName ?? 'current activity'}`,
        category: 'navigate',
        priority: 'high',
        actionType: 'open_activity',
        payload: {
          type: 'open_activity',
          activityId: context.currentActivityId,
          stageId: context.currentStageId ?? undefined,
        },
        enabled: true,
      },
      {
        id: 'quick-activity-template',
        label: 'Generate template',
        category: 'create',
        priority: 'medium',
        actionType: 'generate_template',
        payload: {
          type: 'generate_template',
          templateType: context.currentActivityCanvasType ?? 'artifact',
          targetActivityId: context.currentActivityId,
        },
        enabled: true,
      },
      {
        id: 'quick-activity-prereqs',
        label: 'Check prerequisites',
        category: 'review',
        priority: 'medium',
        actionType: 'show_prerequisites',
        payload: {
          type: 'show_prerequisites',
          activityId: context.currentActivityId,
          prerequisiteIds: context.incompletePrerequisites.map((item) => item.activityId),
        },
        enabled: true,
      },
      {
        id: 'quick-activity-question',
        label: 'Ask a question',
        category: 'review',
        priority: 'low',
        actionType: 'custom',
        payload: { type: 'custom', actionKey: 'ask_question' },
        enabled: true,
      },
    ];
  }, [context]);

  const showTypingIndicator =
    aiState === 'thinking' || aiState === 'streaming' || aiState === 'tool_use';

  return (
    <div className={styles.messages}>
      {messages.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.welcomeCard}>
            <h3 className={styles.welcomeTitle}>Welcome to your project assistant.</h3>
            <p className={styles.welcomeText}>
              I can help you navigate your project methodology, suggest next actions,
              generate templates, and answer questions about your project.
            </p>
            <div className={styles.quickStartList}>
              {quickStartChips.map((chip) =>
                renderActionChip ? (
                  <span key={chip.id} className={styles.quickStartItem}>
                    {renderActionChip(chip)}
                  </span>
                ) : (
                  <ActionChipButton key={chip.id} chip={chip} onClick={() => onChipClick(chip)} />
                )
              )}
            </div>
          </div>
        </div>
      ) : (
        messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            renderActionChip={(chip, options) =>
              renderActionChip ? (
                renderActionChip(chip, options)
              ) : (
                <ActionChipButton chip={chip} onClick={() => onChipClick(chip)} small={options?.small} />
              )
            }
          />
        ))
      )}

      {showTypingIndicator && (
        <div className={`${bubbleStyles.message} ${bubbleStyles.assistant} ${styles.typingBubble}`}>
          <div className={styles.typingDots} aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <span className={styles.typingLabel}>
            {typingStateLabels[aiState as keyof typeof typingStateLabels]}
          </span>
        </div>
      )}

      <div ref={scrollAnchorRef} />
    </div>
  );
}

interface ActionChipButtonProps {
  chip: ActionChip;
  onClick: () => void;
  small?: boolean;
}

function ActionChipButton({ chip, onClick, small = false }: ActionChipButtonProps) {
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
