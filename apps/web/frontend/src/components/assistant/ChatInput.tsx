import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent, KeyboardEvent, RefObject } from 'react';
import { Icon } from '@/components/icon/Icon';
import { FocusTrap } from '@/components/ui/FocusTrap';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { usePromptStore } from '@/store/prompts';
import { PromptPicker } from './PromptPicker';
import styles from './ChatInput.module.css';

const MIN_HEIGHT = 56;
const MAX_HEIGHT = 168;

const SLASH_COMMANDS = [
  { command: '/prompt', description: 'Open prompt picker' },
  { command: '/research', description: 'Start scope research' },
  { command: '/help', description: 'Send help request' },
  { command: '/status', description: 'Send status request' },
] as const;

interface ChatInputProps {
  error?: string | null;
  inputRef?: RefObject<HTMLTextAreaElement>;
  onSubmitMessage: (message: string) => Promise<void> | void;
  onStartScopeResearch: () => void;
}

export function ChatInput({ error, inputRef, onSubmitMessage, onStartScopeResearch }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [activeCommandIndex, setActiveCommandIndex] = useState(0);
  const [promptPickerOpen, setPromptPickerOpen] = useState(false);
  const [researchConfirmOpen, setResearchConfirmOpen] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const internalTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  const prompts = usePromptStore((state) => state.prompts);
  const hydratePrompts = usePromptStore((state) => state.hydratePrompts);

  const textareaRef = inputRef ?? internalTextareaRef;

  const slashQuery = value.startsWith('/') ? value.toLowerCase() : '';
  const slashOptions = useMemo(
    () =>
      SLASH_COMMANDS.filter((item) =>
        item.command.toLowerCase().startsWith(slashQuery)
      ),
    [slashQuery]
  );
  const slashOpen = slashQuery.length > 0 && !promptPickerOpen && slashOptions.length > 0;
  const showCommandHint = inputFocused && value.trim().length === 0 && !slashOpen;

  const resizeTextarea = useCallback(() => {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = `${Math.max(MIN_HEIGHT, Math.min(textareaRef.current.scrollHeight, MAX_HEIGHT))}px`;
  }, [textareaRef]);

  const openPromptPicker = () => {
    setPromptPickerOpen(true);
    hydratePrompts();
  };

  const runCommand = async (command: string) => {
    setValue('');
    setActiveCommandIndex(0);

    if (command === '/prompt') {
      openPromptPicker();
      return;
    }

    if (command === '/research') {
      setResearchConfirmOpen(true);
      return;
    }

    if (command === '/help') {
      await onSubmitMessage('help');
      return;
    }

    if (command === '/status') {
      await onSubmitMessage('status');
    }
  };

  const submitCurrent = async () => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }

    if (trimmed.startsWith('/')) {
      const option = slashOptions[activeCommandIndex] ?? slashOptions[0];
      if (option) {
        await runCommand(option.command);
        resizeTextarea();
      }
      return;
    }

    await onSubmitMessage(trimmed);
    setValue('');
    setPromptPickerOpen(false);
    resizeTextarea();
  };

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(event.target.value);
    setPromptPickerOpen(false);
  };

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashOpen && event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveCommandIndex((prev) => (prev + 1) % slashOptions.length);
      return;
    }

    if (slashOpen && event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveCommandIndex((prev) => (prev - 1 + slashOptions.length) % slashOptions.length);
      return;
    }

    if ((slashOpen || promptPickerOpen) && event.key === 'Escape') {
      event.preventDefault();
      setPromptPickerOpen(false);
      setValue((prev) => (prev.startsWith('/') ? '' : prev));
      return;
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();

      if (slashOpen) {
        const option = slashOptions[activeCommandIndex] ?? slashOptions[0];
        if (option) {
          await runCommand(option.command);
          resizeTextarea();
        }
        return;
      }

      await submitCurrent();
    }
  };

  useEffect(() => {
    resizeTextarea();
  }, [resizeTextarea, value]);

  useEffect(() => {
    if (activeCommandIndex > slashOptions.length - 1) {
      setActiveCommandIndex(0);
    }
  }, [activeCommandIndex, slashOptions.length]);

  return (
    <form
      className={styles.inputArea}
      onSubmit={async (event: FormEvent) => {
        event.preventDefault();
        await submitCurrent();
      }}
    >
      {error && (
        <p className={styles.inputError} role="alert">
          {error}
        </p>
      )}

      {slashOpen && (
        <FocusTrap
          className={styles.slashPopover}
          role="listbox"
          aria-label="Slash commands"
          onClose={() => setValue('')}
        >
          {slashOptions.map((option, index) => (
            <button
              type="button"
              key={option.command}
              className={`${styles.slashOption} ${index === activeCommandIndex ? styles.slashOptionActive : ''}`}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                void runCommand(option.command);
              }}
            >
              <span className={styles.optionLabel}>{option.command}</span>
              <span className={styles.optionDescription}>{option.description}</span>
            </button>
          ))}
        </FocusTrap>
      )}

      {promptPickerOpen && (
        <PromptPicker
          prompts={prompts}
          onClose={() => {
            setPromptPickerOpen(false);
            requestAnimationFrame(() => {
              textareaRef.current?.focus();
            });
          }}
          onSelectPrompt={(prompt) => {
            setValue(prompt.description);
          }}
        />
      )}

      {researchConfirmOpen && (
        <ConfirmDialog
          title="Start scope research?"
          description="This will start a background research operation for your current context."
          confirmLabel="Start research"
          cancelLabel="Cancel"
          onCancel={() => setResearchConfirmOpen(false)}
          onConfirm={() => {
            onStartScopeResearch();
            setResearchConfirmOpen(false);
          }}
        />
      )}

      <div className={styles.inputRow}>
        <label className={styles.visuallyHidden} htmlFor="assistant-chat-input">
          AI assistant chat input
        </label>
        <textarea
          rows={2}
          className={styles.textarea}
          placeholder="Type a message or / for commands"
          value={value}
          onChange={handleChange}
          onKeyDown={(event) => {
            void handleKeyDown(event);
          }}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          ref={textareaRef}
          id="assistant-chat-input"
        />
        <button
          type="button"
          className={styles.promptButton}
          onClick={openPromptPicker}
          title="Open prompt picker"
          aria-label="Open prompt picker"
        >
          <Icon
            semantic="artifact.document"
            label="Open prompt picker"
          />
        </button>
        <button
          type="submit"
          className={styles.sendButton}
          disabled={!value.trim()}
          title="Send message"
        >
          <Icon
            semantic="communication.send"
            label="Send message"
          />
        </button>
      </div>

      {showCommandHint && (
        <div className={styles.commandHintRow} aria-live="polite">
          {SLASH_COMMANDS.map((option) => (
            <span key={option.command} className={styles.commandHintItem}>
              <strong>{option.command}</strong> {option.description}
            </span>
          ))}
        </div>
      )}
    </form>
  );
}

export default ChatInput;
