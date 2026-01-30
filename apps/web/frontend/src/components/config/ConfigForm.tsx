import { useEffect, useMemo, useState } from 'react';
import styles from './ConfigForm.module.css';

export type ConfigFieldType =
  | 'text'
  | 'number'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'textarea'
  | 'url';

export interface ConfigFieldDefinition {
  name: string;
  label: string;
  type: ConfigFieldType;
  required?: boolean;
  description?: string;
  options?: string[];
  min?: number;
  max?: number;
  placeholder?: string;
}

interface ConfigFormProps {
  title: string;
  description?: string;
  fields: ConfigFieldDefinition[];
  initialValues: Record<string, unknown>;
  submitLabel?: string;
  onSubmit: (values: Record<string, unknown>) => Promise<void>;
}

interface FieldError {
  name: string;
  message: string;
}

const normalizeValue = (value: unknown, field: ConfigFieldDefinition): unknown => {
  if (field.type === 'boolean') {
    return Boolean(value);
  }
  if (field.type === 'multiselect') {
    return Array.isArray(value) ? value.map(String) : [];
  }
  if (field.type === 'number') {
    if (value === '' || value === null || value === undefined) return '';
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isNaN(numeric) ? '' : numeric;
  }
  return value ?? '';
};

export function ConfigForm({
  title,
  description,
  fields,
  initialValues,
  submitLabel = 'Save changes',
  onSubmit,
}: ConfigFormProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const nextValues: Record<string, unknown> = {};
    fields.forEach((field) => {
      nextValues[field.name] = normalizeValue(initialValues[field.name], field);
    });
    setValues(nextValues);
    setErrors([]);
    setSubmitError(null);
  }, [fields, initialValues]);

  const errorMap = useMemo(() => {
    return errors.reduce<Record<string, string>>((acc, error) => {
      acc[error.name] = error.message;
      return acc;
    }, {});
  }, [errors]);

  const validate = () => {
    const nextErrors: FieldError[] = [];

    fields.forEach((field) => {
      const value = values[field.name];
      if (field.required) {
        if (field.type === 'multiselect' && Array.isArray(value) && value.length === 0) {
          nextErrors.push({
            name: field.name,
            message: `${field.label} is required.`,
          });
          return;
        }

        if (value === '' || value === undefined || value === null) {
          nextErrors.push({
            name: field.name,
            message: `${field.label} is required.`,
          });
          return;
        }
      }

      if (field.type === 'number' && value !== '' && value !== null && value !== undefined) {
        const numeric = typeof value === 'number' ? value : Number(value);
        if (Number.isNaN(numeric)) {
          nextErrors.push({
            name: field.name,
            message: `${field.label} must be a number.`,
          });
          return;
        }
        if (field.min !== undefined && numeric < field.min) {
          nextErrors.push({
            name: field.name,
            message: `${field.label} must be at least ${field.min}.`,
          });
          return;
        }
        if (field.max !== undefined && numeric > field.max) {
          nextErrors.push({
            name: field.name,
            message: `${field.label} must be at most ${field.max}.`,
          });
          return;
        }
      }

      if (field.type === 'url' && value) {
        try {
          new URL(String(value));
        } catch {
          nextErrors.push({
            name: field.name,
            message: `${field.label} must be a valid URL.`,
          });
        }
      }
    });

    setErrors(nextErrors);
    return nextErrors.length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save changes.';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (name: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => prev.filter((error) => error.name !== name));
  };

  const renderFieldControl = (field: ConfigFieldDefinition) => {
    const value = values[field.name];
    const fieldId = `${title}-${field.name}`;

    switch (field.type) {
      case 'textarea':
        return (
          <textarea
            id={fieldId}
            value={String(value ?? '')}
            placeholder={field.placeholder}
            onChange={(event) => handleChange(field.name, event.target.value)}
            className={styles.textarea}
          />
        );
      case 'select':
        return (
          <select
            id={fieldId}
            value={String(value ?? '')}
            onChange={(event) => handleChange(field.name, event.target.value)}
            className={styles.select}
          >
            <option value="">Select an option</option>
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );
      case 'multiselect':
        return (
          <select
            id={fieldId}
            multiple
            value={Array.isArray(value) ? value.map(String) : []}
            onChange={(event) => {
              const selected = Array.from(event.target.selectedOptions).map(
                (option) => option.value
              );
              handleChange(field.name, selected);
            }}
            className={styles.multiselect}
          >
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );
      case 'boolean':
        return (
          <label className={styles.checkboxLabel}>
            <input
              id={fieldId}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(event) => handleChange(field.name, event.target.checked)}
            />
            <span>{field.label}</span>
          </label>
        );
      case 'number':
        return (
          <input
            id={fieldId}
            type="number"
            value={
              value === '' || value === undefined || value === null
                ? ''
                : Number(value)
            }
            placeholder={field.placeholder}
            min={field.min}
            max={field.max}
            onChange={(event) => {
              const nextValue = event.target.value === '' ? '' : Number(event.target.value);
              handleChange(field.name, nextValue);
            }}
            className={styles.input}
          />
        );
      case 'url':
        return (
          <input
            id={fieldId}
            type="url"
            value={String(value ?? '')}
            placeholder={field.placeholder}
            onChange={(event) => handleChange(field.name, event.target.value)}
            className={styles.input}
          />
        );
      default:
        return (
          <input
            id={fieldId}
            type="text"
            value={String(value ?? '')}
            placeholder={field.placeholder}
            onChange={(event) => handleChange(field.name, event.target.value)}
            className={styles.input}
          />
        );
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>{title}</h3>
          {description && <p className={styles.description}>{description}</p>}
        </div>
        <button
          type="submit"
          className={styles.submit}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Saving…' : submitLabel}
        </button>
      </div>
      <div className={styles.fields}>
        {fields.map((field) => (
          <div key={field.name} className={styles.field}>
            {field.type !== 'boolean' && (
              <label htmlFor={`${title}-${field.name}`} className={styles.label}>
                {field.label}
                {field.required && <span className={styles.required}>*</span>}
              </label>
            )}
            {renderFieldControl(field)}
            {field.description && (
              <span className={styles.hint}>{field.description}</span>
            )}
            {errorMap[field.name] && (
              <span className={styles.error}>{errorMap[field.name]}</span>
            )}
          </div>
        ))}
      </div>
      {submitError && <div className={styles.submitError}>{submitError}</div>}
    </form>
  );
}
