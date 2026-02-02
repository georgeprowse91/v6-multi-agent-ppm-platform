import { useEffect, useMemo, useState } from 'react';
import type { PromptDefinition } from '@/types/prompt';
import { usePromptStore } from '@/store/prompts';
import {
  formatPromptTags,
  normalizePromptTags,
  validatePromptFields,
  type PromptFieldErrors,
} from '@/utils/prompts';
import styles from './PromptManager.module.css';

const emptyPrompt = {
  label: '',
  description: '',
  tags: '',
};

export function PromptManager() {
  const { prompts, hydratePrompts, addPrompt, updatePrompt, deletePrompt } =
    usePromptStore();
  const [createFields, setCreateFields] = useState(emptyPrompt);
  const [createErrors, setCreateErrors] = useState<PromptFieldErrors>({});
  const [editPromptId, setEditPromptId] = useState<string | null>(null);
  const [editFields, setEditFields] = useState(emptyPrompt);
  const [editErrors, setEditErrors] = useState<PromptFieldErrors>({});
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    hydratePrompts();
  }, [hydratePrompts]);

  const sortedPrompts = useMemo(
    () => [...prompts].sort((a, b) => a.label.localeCompare(b.label)),
    [prompts]
  );

  const handleCreateChange = (
    field: keyof typeof createFields,
    value: string
  ) => {
    setCreateFields((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const errors = validatePromptFields(createFields);
    setCreateErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    const newPrompt: PromptDefinition = {
      id: crypto.randomUUID(),
      label: createFields.label.trim(),
      description: createFields.description.trim(),
      tags: normalizePromptTags(createFields.tags),
    };
    addPrompt(newPrompt);
    setCreateFields(emptyPrompt);
    setStatusMessage('Prompt created.');
  };

  const startEdit = (prompt: PromptDefinition) => {
    setEditPromptId(prompt.id);
    setEditFields({
      label: prompt.label,
      description: prompt.description,
      tags: formatPromptTags(prompt.tags),
    });
    setEditErrors({});
  };

  const handleEditChange = (field: keyof typeof editFields, value: string) => {
    setEditFields((prev) => ({ ...prev, [field]: value }));
  };

  const handleEditSave = () => {
    if (!editPromptId) return;
    const errors = validatePromptFields(editFields);
    setEditErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    updatePrompt(editPromptId, {
      label: editFields.label.trim(),
      description: editFields.description.trim(),
      tags: normalizePromptTags(editFields.tags),
    });
    setEditPromptId(null);
    setEditFields(emptyPrompt);
    setStatusMessage('Prompt updated.');
  };

  const handleEditCancel = () => {
    setEditPromptId(null);
    setEditErrors({});
    setEditFields(emptyPrompt);
  };

  const handleDelete = (prompt: PromptDefinition) => {
    const confirmed = window.confirm(`Delete "${prompt.label}"?`);
    if (!confirmed) return;
    deletePrompt(prompt.id);
    if (editPromptId === prompt.id) {
      handleEditCancel();
    }
    setStatusMessage('Prompt deleted.');
  };

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Prompt Manager</h1>
        <p className={styles.subtitle}>
          Create, edit, and organize assistant prompts for the team.
        </p>
      </header>

      {statusMessage && <p className={styles.status}>{statusMessage}</p>}

      <section className={styles.panel}>
        <h2 className={styles.panelTitle}>Create a new prompt</h2>
        <form className={styles.form} onSubmit={handleCreateSubmit}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Label</span>
            <input
              type="text"
              value={createFields.label}
              onChange={(event) => handleCreateChange('label', event.target.value)}
              placeholder="e.g., Draft kickoff agenda"
            />
            {createErrors.label && (
              <span className={styles.fieldError}>{createErrors.label}</span>
            )}
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Description</span>
            <textarea
              value={createFields.description}
              onChange={(event) =>
                handleCreateChange('description', event.target.value)
              }
              placeholder="Describe the prompt you want the assistant to run."
            />
            {createErrors.description && (
              <span className={styles.fieldError}>{createErrors.description}</span>
            )}
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Tags</span>
            <input
              type="text"
              value={createFields.tags}
              onChange={(event) => handleCreateChange('tags', event.target.value)}
              placeholder="planning, kickoff"
            />
            <p className={styles.fieldHint}>Separate tags with commas.</p>
            {createErrors.tags && (
              <span className={styles.fieldError}>{createErrors.tags}</span>
            )}
          </label>
          <div className={styles.actions}>
            <button type="submit" className={styles.primaryButton}>
              Save prompt
            </button>
          </div>
        </form>
      </section>

      <section className={styles.panel}>
        <h2 className={styles.panelTitle}>Existing prompts</h2>
        {sortedPrompts.length === 0 ? (
          <p className={styles.emptyState}>No prompts yet. Create one above.</p>
        ) : (
          <div className={styles.promptList}>
            {sortedPrompts.map((prompt) => (
              <div key={prompt.id} className={styles.promptCard}>
                <div className={styles.promptHeader}>
                  <h3 className={styles.promptTitle}>{prompt.label}</h3>
                  <div className={styles.promptActions}>
                    <button
                      type="button"
                      className={styles.actionButton}
                      onClick={() => startEdit(prompt)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className={`${styles.actionButton} ${styles.actionButtonDanger}`}
                      onClick={() => handleDelete(prompt)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <p className={styles.promptDescription}>{prompt.description}</p>
                <div className={styles.tags}>
                  {prompt.tags.map((tag) => (
                    <span key={tag} className={styles.tag}>
                      {tag}
                    </span>
                  ))}
                </div>
                {editPromptId === prompt.id && (
                  <div className={styles.form}>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Label</span>
                      <input
                        type="text"
                        value={editFields.label}
                        onChange={(event) =>
                          handleEditChange('label', event.target.value)
                        }
                      />
                      {editErrors.label && (
                        <span className={styles.fieldError}>{editErrors.label}</span>
                      )}
                    </label>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Description</span>
                      <textarea
                        value={editFields.description}
                        onChange={(event) =>
                          handleEditChange('description', event.target.value)
                        }
                      />
                      {editErrors.description && (
                        <span className={styles.fieldError}>
                          {editErrors.description}
                        </span>
                      )}
                    </label>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Tags</span>
                      <input
                        type="text"
                        value={editFields.tags}
                        onChange={(event) =>
                          handleEditChange('tags', event.target.value)
                        }
                      />
                      {editErrors.tags && (
                        <span className={styles.fieldError}>{editErrors.tags}</span>
                      )}
                    </label>
                    <div className={styles.actions}>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={handleEditCancel}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className={styles.primaryButton}
                        onClick={handleEditSave}
                      >
                        Save changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

export default PromptManager;
