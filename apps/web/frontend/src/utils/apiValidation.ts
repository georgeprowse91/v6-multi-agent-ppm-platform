import { Schema, SchemaValidationError, type ValidationIssue } from '@/utils/schema';

export class PayloadValidationError extends Error {
  readonly issues: ValidationIssue[];

  constructor(message: string, issues: ValidationIssue[]) {
    super(message);
    this.name = 'PayloadValidationError';
    this.issues = issues;
  }
}

export const reportPayloadValidationError = (
  context: string,
  issues: ValidationIssue[],
  payload: unknown
) => {
  console.error(`[telemetry] Invalid payload for ${context}`, {
    context,
    issues,
    payload,
  });
};

export const parseWithSchema = <T>(schema: Schema<T>, payload: unknown, context: string): T => {
  try {
    return schema.parse(payload);
  } catch (error) {
    if (error instanceof SchemaValidationError) {
      reportPayloadValidationError(context, error.issues, payload);
      throw new PayloadValidationError(`Invalid ${context} payload`, error.issues);
    }
    throw error;
  }
};

export const parseJsonResponse = async <T>(
  response: Response,
  schema: Schema<T>,
  context: string
): Promise<T> => {
  const payload = await response.json();
  return parseWithSchema(schema, payload, context);
};
