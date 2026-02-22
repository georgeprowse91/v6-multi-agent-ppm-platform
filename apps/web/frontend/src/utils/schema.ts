export interface ValidationIssue {
  path: string;
  message: string;
}

export class SchemaValidationError extends Error {
  readonly issues: ValidationIssue[];

  constructor(message: string, issues: ValidationIssue[]) {
    super(message);
    this.name = 'SchemaValidationError';
    this.issues = issues;
  }
}

export interface Schema<T> {
  parse: (input: unknown, path?: string) => T;
  optional: () => Schema<T | undefined>;
  nullish: () => Schema<T | null | undefined>;
  default: (value: T) => Schema<T>;
}

type Parser<T> = (input: unknown, path: string) => T;

const makeSchema = <T>(parser: Parser<T>): Schema<T> => ({
  parse: (input, path = '$') => parser(input, path),
  optional() {
    return makeSchema<T | undefined>((input, path) => {
      if (input === undefined) return undefined;
      return parser(input, path);
    });
  },
  nullish() {
    return makeSchema<T | null | undefined>((input, path) => {
      if (input === undefined || input === null) return input as null | undefined;
      return parser(input, path);
    });
  },
  default(value: T) {
    return makeSchema<T>((input, path) => {
      if (input === undefined) return value;
      return parser(input, path);
    });
  },
});

const fail = (path: string, message: string): never => {
  throw new SchemaValidationError('Schema validation failed', [{ path, message }]);
};

const mergeIssues = (error: unknown, path: string, fallback: string): never => {
  if (error instanceof SchemaValidationError) {
    throw error;
  }
  throw new SchemaValidationError('Schema validation failed', [{ path, message: fallback }]);
};

export const s = {
  string: () =>
    makeSchema<string>((input, path) => {
      if (typeof input !== 'string') fail(path, 'Expected string');
      return input as string;
    }),
  number: () =>
    makeSchema<number>((input, path) => {
      if (typeof input !== 'number' || !Number.isFinite(input)) fail(path, 'Expected number');
      return input as number;
    }),
  boolean: () =>
    makeSchema<boolean>((input, path) => {
      if (typeof input !== 'boolean') fail(path, 'Expected boolean');
      return input as boolean;
    }),
  unknown: () => makeSchema<unknown>((input) => input),
  enum: <T extends readonly string[]>(values: T) =>
    makeSchema<T[number]>((input, path) => {
      if (typeof input !== 'string' || !values.includes(input)) {
        fail(path, `Expected one of: ${values.join(', ')}`);
      }
      return input as T[number];
    }),
  array: <T>(item: Schema<T>) =>
    makeSchema<T[]>((input, path) => {
      if (!Array.isArray(input)) fail(path, 'Expected array');
      return (input as unknown[]).map((entry: unknown, index: number) => item.parse(entry, `${path}[${index}]`));
    }),
  record: <T>(item: Schema<T>) =>
    makeSchema<Record<string, T>>((input, path) => {
      if (!input || typeof input !== 'object' || Array.isArray(input)) fail(path, 'Expected object');
      const entries = Object.entries(input as Record<string, unknown>).map(([k, v]) => [k, item.parse(v, `${path}.${k}`)]);
      return Object.fromEntries(entries);
    }),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic object builder requires any to infer per-field types
  object: <T extends Record<string, Schema<any>>>(shape: T) =>
    makeSchema<{ [K in keyof T]: ReturnType<T[K]['parse']> }>((input, path) => {
      if (!input || typeof input !== 'object' || Array.isArray(input)) fail(path, 'Expected object');
      const source = input as Record<string, unknown>;
      const out: Record<string, unknown> = {};
      for (const [key, schema] of Object.entries(shape)) {
        try {
          out[key] = schema.parse(source[key], `${path}.${key}`);
        } catch (error) {
          mergeIssues(error, `${path}.${key}`, 'Invalid field');
        }
      }
      return out as { [K in keyof T]: ReturnType<T[K]['parse']> };
    }),
};
