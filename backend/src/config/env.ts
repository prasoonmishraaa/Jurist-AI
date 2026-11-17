import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const nodeEnv = process.env.NODE_ENV || 'development';
const devFallbackSecret = 'jurist-ai-dev-jwt-secret-local-only';

if (nodeEnv === 'production' && !process.env.JWT_SECRET) {
  console.error('[CRITICAL] JWT_SECRET is not set in production environment. Authentication will refuse requests until JWT_SECRET is configured.');
}

export const env = {
  PORT: parseInt(process.env.PORT || '5001', 10),
  NODE_ENV: nodeEnv,
  MONGODB_URI: process.env.MONGODB_URI || '',
  JWT_SECRET: process.env.JWT_SECRET || (nodeEnv === 'production' ? '' : devFallbackSecret),
  IS_JWT_SECRET_CONFIGURED: Boolean(process.env.JWT_SECRET),
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '7d',
  ML_SERVICE_URL: process.env.ML_SERVICE_URL || 'http://localhost:8000',
  INTERNAL_ML_SECRET: process.env.INTERNAL_ML_SECRET || 'jurist-internal-secret-key',
  CORS_ORIGIN: process.env.CORS_ORIGIN
    ? process.env.CORS_ORIGIN.split(',').map(s => s.trim()).filter(Boolean)
    : ['http://localhost:5173', 'http://localhost:3000'],
  MAX_FILE_SIZE_MB: parseInt(process.env.MAX_FILE_SIZE_MB || '15', 10),
  DOCUMENT_EXTRACTION_TIMEOUT_MS: parseInt(process.env.DOCUMENT_EXTRACTION_TIMEOUT_MS || '60000', 10),
  UPLOAD_DIR: process.env.UPLOAD_DIR || path.resolve(__dirname, '../../uploads')
};
