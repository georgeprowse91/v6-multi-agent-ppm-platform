import { Fragment, type ReactNode } from 'react';
import { Icon } from '@/components/icon/Icon';
import type { ActionChip, AssistantMessage } from '@/store/assistant';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  message: AssistantMessage;
  renderActionChip?: (chip: ActionChip, options?: { small?: boolean }) => ReactNode;
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

function renderNestedList(lines: string[]): ReactNode {
  const root: Array<{ type: 'ul' | 'ol'; items: Array<{ text: string; children: typeof root }> }> = [];
  const stack: Array<{ level: number; node: { type: 'ul' | 'ol'; items: Array<{ text: string; children: typeof root }> } }> = [];

  const getContainer = (level: number, type: 'ul' | 'ol') => {
    while (stack.length > 0 && stack[stack.length - 1].level >= level) {
      stack.pop();
    }

    const parent = stack[stack.length - 1];
    const target = parent?.node.items[parent.node.items.length - 1]?.children ?? root;
    const existing = target[target.length - 1];

    if (!existing || existing.type !== type) {
      const next = { type, items: [] as Array<{ text: string; children: typeof root }> };
      target.push(next);
      stack.push({ level, node: next });
      return next;
    }

    stack.push({ level, node: existing });
    return existing;
  };

  lines.forEach((line) => {
    const match = line.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
    if (!match) return;

    const level = Math.floor(match[1].length / 2);
    const type = /\d+\./.test(match[2]) ? 'ol' : 'ul';
    const text = match[3];

    const container = getContainer(level, type);
    container.items.push({ text, children: [] });
  });

  const renderNodes = (nodes: typeof root, keyPrefix: string): ReactNode[] =>
    nodes.map((node, nodeIndex) => {
      const ListTag = node.type;
      return (
        <ListTag key={`${keyPrefix}-${nodeIndex}`}>
          {node.items.map((item, itemIndex) => (
            <li key={`${keyPrefix}-${nodeIndex}-${itemIndex}`}>
              <MarkdownInline text={item.text} />
              {item.children.length > 0 ? renderNodes(item.children, `${keyPrefix}-${nodeIndex}-${itemIndex}`) : null}
            </li>
          ))}
        </ListTag>
      );
    });

  return <>{renderNodes(root, 'nested-list')}</>;
}

function renderAssistantMarkdown(content: string): ReactNode {
  const lines = content.split('\n');
  const blocks: ReactNode[] = [];
  let paragraphLines: string[] = [];
  let listLines: string[] = [];
  let tableLines: string[] = [];
  let blockquoteLines: string[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeBlockLanguage = '';

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return;
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
    if (listLines.length === 0) return;
    blocks.push(<div key={`list-${blocks.length}`}>{renderNestedList(listLines)}</div>);
    listLines = [];
  };

  const flushTable = () => {
    if (tableLines.length < 2) {
      tableLines = [];
      return;
    }

    const rows = tableLines.map((line) =>
      line
        .split('|')
        .map((cell) => cell.trim())
        .filter((cell, index, arr) => !(index === 0 && cell === '') && !(index === arr.length - 1 && cell === ''))
    );
    const [header, ...bodyRows] = rows;
    const normalizedBody = bodyRows.filter((row, idx) => !(idx === 0 && row.every((cell) => /^:?-{3,}:?$/.test(cell))));

    blocks.push(
      <div key={`table-wrap-${blocks.length}`} className={styles.tableWrap}>
        <table>
          <thead>
            <tr>
              {header.map((cell, index) => (
                <th key={`th-${index}`}><MarkdownInline text={cell} /></th>
              ))}
            </tr>
          </thead>
          <tbody>
            {normalizedBody.map((row, rowIndex) => (
              <tr key={`tr-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`td-${rowIndex}-${cellIndex}`}><MarkdownInline text={cell} /></td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableLines = [];
  };

  const flushBlockquote = () => {
    if (blockquoteLines.length === 0) return;
    blocks.push(
      <blockquote key={`bq-${blocks.length}`}>
        {blockquoteLines.map((line, index) => (
          <Fragment key={`bq-line-${index}`}>
            <MarkdownInline text={line} />
            {index < blockquoteLines.length - 1 && <br />}
          </Fragment>
        ))}
      </blockquote>
    );
    blockquoteLines = [];
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
        flushTable();
        flushBlockquote();
        codeBlockLanguage = codeFenceMatch[1] ?? '';
      }

      inCodeBlock = !inCodeBlock;
      return;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    const listMatch = line.match(/^\s*([-*]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      flushTable();
      flushBlockquote();
      listLines.push(line);
      return;
    }

    if (line.trim().startsWith('|')) {
      flushParagraph();
      flushList();
      flushBlockquote();
      tableLines.push(line);
      return;
    }

    const blockquoteMatch = line.match(/^>\s?(.*)$/);
    if (blockquoteMatch) {
      flushParagraph();
      flushList();
      flushTable();
      blockquoteLines.push(blockquoteMatch[1]);
      return;
    }

    if (line.trim() === '') {
      flushParagraph();
      flushList();
      flushTable();
      flushBlockquote();
      return;
    }

    flushList();
    flushTable();
    flushBlockquote();
    paragraphLines.push(line);
  });

  if (inCodeBlock) {
    flushCodeBlock();
  }

  flushParagraph();
  flushList();
  flushTable();
  flushBlockquote();

  return <div className={styles.messageContentRendered}>{blocks}</div>;
}

export function MessageBubble({
  message,
  renderActionChip
}: MessageBubbleProps) {
  const showGeneratedBadge = message.role === 'assistant';

  return (
    <div
      className={`${styles.message} ${styles[message.role]} ${message.isWarning ? styles.warning : ''}`}
    >
      {showGeneratedBadge && (
        <span
          className={styles.generatedBadgeTopRight}
          title="This response was generated by the AI assistant."
        >
          <Icon semantic="ai.automation" label="AI generated response" size="sm" />
          Generated
        </span>
      )}
      <div className={styles.messageContent}>
        {message.role === 'assistant' ? renderAssistantMarkdown(message.content) : message.content}
      </div>
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
