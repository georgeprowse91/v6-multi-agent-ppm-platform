import { Fragment, type ReactNode } from 'react';
import type {
  ActionChip,
  AssistantMessage,
  ConversationalCommandMessageData,
  ScopeResearchItem,
  ScopeResearchMessageData,
} from '@/store/assistant';
import { ScopeResearchCard } from './ScopeResearchCard';
import { ConversationalCommandCard } from './ConversationalCommandCard';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  message: AssistantMessage;
  renderActionChip?: (chip: ActionChip, options?: { small?: boolean }) => ReactNode;
  onApplyScopeResearch?: (data: ScopeResearchMessageData, acceptedItems: ScopeResearchItem[]) => boolean;
  onApplyConversationalCommand?: (data: ConversationalCommandMessageData) => void;
  onCancelConversationalCommand?: () => void;
}

interface MarkdownInlineProps {
  text: string;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const segments: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    const key = `${match.index}-${token.length}`;

    if (token.startsWith('**') && token.endsWith('**')) {
      segments.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      segments.push(<em key={key}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      segments.push(<code key={key}>{token.slice(1, -1)}</code>);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    segments.push(text.slice(lastIndex));
  }

  return segments;
}

function MarkdownInline({ text }: MarkdownInlineProps) {
  const pieces = renderInlineMarkdown(text);

  return (
    <>
      {pieces.map((piece, index) => (
        <Fragment key={index}>{piece}</Fragment>
      ))}
    </>
  );
}

function renderAssistantMarkdown(content: string): ReactNode {
  const lines = content.split('\n');
  const blocks: ReactNode[] = [];
  let paragraphLines: string[] = [];
  let listItems: string[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeBlockLanguage = '';

  const flushParagraph = () => {
    if (paragraphLines.length === 0) {
      return;
    }

    blocks.push(
      <p key={`p-${blocks.length}`}>
        {paragraphLines.map((line, index) => (
          <Fragment key={`line-${index}`}>
            <MarkdownInline text={line} />
            {index < paragraphLines.length - 1 && <br />}
          </Fragment>
        ))}
      </p>
    );

    paragraphLines = [];
  };

  const flushList = () => {
    if (listItems.length === 0) {
      return;
    }

    blocks.push(
      <ul key={`ul-${blocks.length}`}>
        {listItems.map((item, index) => (
          <li key={`li-${index}`}>
            <MarkdownInline text={item} />
          </li>
        ))}
      </ul>
    );

    listItems = [];
  };

  const flushCodeBlock = () => {
    blocks.push(
      <pre key={`pre-${blocks.length}`}>
        <code className={codeBlockLanguage ? `language-${codeBlockLanguage}` : undefined}>
          {codeLines.join('\n')}
        </code>
      </pre>
    );

    codeLines = [];
    codeBlockLanguage = '';
  };

  lines.forEach((line) => {
    const codeFenceMatch = line.match(/^```\s*([\w-]+)?\s*$/);

    if (codeFenceMatch) {
      if (inCodeBlock) {
        flushCodeBlock();
      } else {
        flushParagraph();
        flushList();
        codeBlockLanguage = codeFenceMatch[1] ?? '';
      }

      inCodeBlock = !inCodeBlock;
      return;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    const listMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      listItems.push(listMatch[1]);
      return;
    }

    if (line.trim() === '') {
      flushParagraph();
      flushList();
      return;
    }

    flushList();
    paragraphLines.push(line);
  });

  if (inCodeBlock) {
    flushCodeBlock();
  }

  flushParagraph();
  flushList();

  return <div className={styles.messageContentRendered}>{blocks}</div>;
}

export function MessageBubble({
  message,
  renderActionChip,
  onApplyScopeResearch,
  onApplyConversationalCommand,
  onCancelConversationalCommand,
}: MessageBubbleProps) {
  const showGeneratedBadge = message.role === 'assistant' && message.provenance?.showModelOrTool === true;

  return (
    <div
      className={`${styles.message} ${styles[message.role]} ${message.isWarning ? styles.warning : ''}`}
    >
      <div className={styles.messageContent}>
        {message.role === 'assistant' ? renderAssistantMarkdown(message.content) : message.content}
      </div>
      {message.messageType === 'scope_research' && message.data && (
        <ScopeResearchCard
          data={message.data as ScopeResearchMessageData}
          onApplyAcceptedItems={(data, acceptedItems) =>
            onApplyScopeResearch ? onApplyScopeResearch(data, acceptedItems) : false
          }
        />
      )}
      {message.messageType === 'conversational_command' && message.data && (
        <ConversationalCommandCard
          data={message.data as ConversationalCommandMessageData}
          onCancel={() => onCancelConversationalCommand?.()}
          onApply={(data) => onApplyConversationalCommand?.(data)}
        />
      )}
      {message.sources && message.sources.length > 0 && (
        <ul className={styles.messageSources}>
          {message.sources.map((source) => (
            <li key={source}>{source}</li>
          ))}
        </ul>
      )}
      {message.actionChips && message.actionChips.length > 0 && (
        <div className={styles.messageChips}>
          {message.actionChips.map((chip) => (
            <span key={chip.id}>{renderActionChip?.(chip, { small: true })}</span>
          ))}
        </div>
      )}
      <div className={styles.messageMeta}>
        {showGeneratedBadge && <span className={styles.generatedBadge}>Generated</span>}
        {message.role === 'assistant' && (!message.sources || message.sources.length === 0) && (
          <span className={styles.noSourcesBadge}>No sources</span>
        )}
        <time className={styles.messageTime}>
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>
    </div>
  );
}
