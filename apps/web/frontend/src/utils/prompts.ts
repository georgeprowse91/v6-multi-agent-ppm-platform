export interface PromptFieldErrors {
  label?: string;
  description?: string;
  tags?: string;
}

export interface PromptFields {
  label: string;
  description: string;
  tags: string[] | string;
}

const uniqueTags = (tags: string[]) =>
  Array.from(new Set(tags.map((tag) => tag.toLowerCase())));

export const parsePromptTags = (value: string): string[] =>
  uniqueTags(
    value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)
  );

export const formatPromptTags = (tags: string[]): string => tags.join(', ');

export const normalizePromptTags = (tags: string[] | string): string[] =>
  Array.isArray(tags) ? uniqueTags(tags.map((tag) => tag.trim()).filter(Boolean)) : parsePromptTags(tags);

export const validatePromptFields = (fields: PromptFields): PromptFieldErrors => {
  const errors: PromptFieldErrors = {};
  if (!fields.label.trim()) {
    errors.label = 'Label is required.';
  }
  if (!fields.description.trim()) {
    errors.description = 'Description is required.';
  }
  const tagValues = normalizePromptTags(fields.tags);
  if (tagValues.length === 0) {
    errors.tags = 'Please add at least one tag.';
  }
  return errors;
};
