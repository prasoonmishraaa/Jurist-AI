const SENSITIVE_KEYS = new Set([
  'password',
  'passwordHash',
  'token',
  'authorization',
  'jwt',
  'secret',
  'text',
  'description',
  'fullText',
  'extractedTextSnippet',
  'inputTextSnippet'
]);

const sanitizeArg = (arg: any): any => {
  if (!arg || typeof arg !== 'object') return arg;
  if (arg instanceof Error) return arg.message;
  if (Array.isArray(arg)) return `[Array(${arg.length})]`;

  const sanitized: Record<string, any> = {};
  for (const [k, v] of Object.entries(arg)) {
    sanitized[k] = SENSITIVE_KEYS.has(k) ? '[REDACTED]' : v;
  }
  return sanitized;
};

export const logger = {
  info: (msg: string, ...args: any[]) => {
    console.log(`[INFO] ${new Date().toISOString()} - ${msg}`, ...args.map(sanitizeArg));
  },
  warn: (msg: string, ...args: any[]) => {
    console.warn(`[WARN] ${new Date().toISOString()} - ${msg}`, ...args.map(sanitizeArg));
  },
  error: (msg: string, ...args: any[]) => {
    console.error(`[ERROR] ${new Date().toISOString()} - ${msg}`, ...args.map(sanitizeArg));
  },
  debug: (msg: string, ...args: any[]) => {
    if (process.env.DEBUG === 'true' && process.env.NODE_ENV !== 'production') {
      console.debug(`[DEBUG] ${new Date().toISOString()} - ${msg}`, ...args.map(sanitizeArg));
    }
  }
};
