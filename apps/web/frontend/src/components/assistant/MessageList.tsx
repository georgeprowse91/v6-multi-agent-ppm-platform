import { useEffect, useMemo, useRef, type ReactNode } from 'react';
import {
  type AIState,
  type ActionChip,
  type AssistantContext,
  type AssistantMessage,
  type ScopeResearchItem,
  type ScopeResearchMessageData,
  type ConversationalCommandMessageData,
} from '@/store/assistant';
import styles from './MessageList.module.css';
import bubbleStyles from './MessageBubble.module.css';
import { ActionChipButton } from './ActionChipButton';
import { MessageBubble } from './MessageBubble';
import { ScopeResearchCard } from './ScopeResearchCard';
import { ConversationalCommandCard } from './ConversationalCommandCard';

interface MessageListProps {
  messages: AssistantMessage[];
  aiState: AIState;
  context: AssistantContext | null;
  onChipClick: (chip: ActionChip) => void;
  renderActionChip?: (chip: ActionChip, options?: { small?: boolean }) => ReactNode;
  onApplyScopeResearch?: (data: ScopeResearchMessageData, acceptedItems: ScopeResearchItem[]) => boolean;
  onApplyConversationalCommand?: (data: ConversationalCommandMessageData) => void;
  onCancelConversationalCommand?: () => void;
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
  onApplyScopeResearch,
  onApplyConversationalCommand,
  onCancelConversationalCommand,
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

  const renderWelcomeCard = (key = 'welcome-empty') => (
    <div key={key} className={styles.empty}>
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
  );

  const renderTypingBubble = (key: string, label: string) => (
    <div key={key} className={`${bubbleStyles.message} ${bubbleStyles.assistant} ${styles.typingBubble}`}>
      <div className={styles.typingDots} aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <span className={styles.typingLabel}>{label}</span>
    </div>
  );

  return (
    <div className={styles.messages}>
      {messages.length === 0
        ? renderWelcomeCard()
        : messages.map((message) => {
            const messageType = message.messageType ?? 'text';

            if (messageType === 'welcome') {
              return renderWelcomeCard(message.id);
            }

            if (messageType === 'typing') {
              const label = typeof message.data?.label === 'string' ? message.data.label : 'Responding…';
              return renderTypingBubble(message.id, label);
            }

            if (messageType === 'scope_research') {
              return (
                <div key={message.id}>
                  {message.content ? (
                    <MessageBubble
                      message={message}
                      renderActionChip={(chip, options) =>
                        renderActionChip ? (
                          renderActionChip(chip, options)
                        ) : (
                          <ActionChipButton chip={chip} onClick={() => onChipClick(chip)} small={options?.small} />
                        )
                      }
                    />
                  ) : null}
                  {message.data ? (
                    <ScopeResearchCard
                      data={message.data as ScopeResearchMessageData}
                      onApplyAcceptedItems={(data, acceptedItems) =>
                        onApplyScopeResearch ? onApplyScopeResearch(data, acceptedItems) : false
                      }
                    />
                  ) : null}
                </div>
              );
            }

            if (messageType === 'conversational_command') {
              return (
                <div key={message.id}>
                  {message.content ? (
                    <MessageBubble
                      message={message}
                      renderActionChip={(chip, options) =>
                        renderActionChip ? (
                          renderActionChip(chip, options)
                        ) : (
                          <ActionChipButton chip={chip} onClick={() => onChipClick(chip)} small={options?.small} />
                        )
                      }
                    />
                  ) : null}
                  {message.data ? (
                    <ConversationalCommandCard
                      data={message.data as unknown as ConversationalCommandMessageData}
                      onCancel={() => onCancelConversationalCommand?.()}
                      onApply={(data) => onApplyConversationalCommand?.(data)}
                    />
                  ) : null}
                </div>
              );
            }

            return (
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
            );
          })}

      {showTypingIndicator &&
        renderTypingBubble(`assistant-state-${aiState}`, typingStateLabels[aiState as keyof typeof typingStateLabels])}

      <div ref={scrollAnchorRef} />
    </div>
  );
}
