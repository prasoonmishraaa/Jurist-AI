import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { env } from './config/env';
import routes from './routes';
import { errorHandler } from './middleware/errorHandler';
import { standardRateLimiter } from './middleware/rateLimiter';
import { getDBStatus } from './config/db';

export const createApp = (): Application => {
  const app = express();

  // Required behind Vercel / reverse proxies for accurate client IP & rate limiting
  app.set('trust proxy', 1);

  // Security headers
  app.use(
    helmet({
      contentSecurityPolicy: false
    })
  );

  // Environment-strict CORS configuration
  app.use(
    cors({
      origin: (origin, callback) => {
        if (!origin) return callback(null, true);
        if (env.CORS_ORIGIN.includes(origin)) {
          return callback(null, true);
        }
        if (env.NODE_ENV !== 'production' && (origin.includes('localhost') || origin.includes('127.0.0.1'))) {
          return callback(null, true);
        }
        if (process.env.ALLOW_VERCEL_PREVIEW === 'true' && /^https:\/\/[a-z0-9-]+\.vercel\.app$/i.test(origin)) {
          return callback(null, true);
        }
        return callback(new Error(`Origin ${origin} not permitted by CORS policy.`));
      },
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'x-internal-secret']
    })
  );

  app.use(express.json({ limit: '15mb' }));
  app.use(express.urlencoded({ extended: true, limit: '15mb' }));

  app.use('/api/', standardRateLimiter);

  app.get('/', (_req, res) => {
    const dbStatus = getDBStatus();
    res.json({
      name: 'Jurist AI API',
      status: 'active',
      persistenceMode: dbStatus.persistenceMode,
      health: '/api/v1/health'
    });
  });

  app.get('/health', (_req, res) => {
    const dbStatus = getDBStatus();
    res.json({
      status: 'ok',
      service: 'Jurist AI',
      persistenceMode: dbStatus.persistenceMode
    });
  });

  app.use('/api/v1', routes);

  app.use('*', (req, res) => {
    res.status(404).json({
      success: false,
      error: `Route [${req.method}] ${req.originalUrl} not found.`
    });
  });

  app.use(errorHandler);

  return app;
};

export const app = createApp();
export default app;
