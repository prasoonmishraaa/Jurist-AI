import { app } from './app';
import { env } from './config/env';
import { connectDB } from './config/db';
import { logger } from './utils/logger';
import { seedPrecedents } from './seed';

const startServer = async () => {
  try {
    const isDBConnected = await connectDB();
    if (isDBConnected) {
      await seedPrecedents();
    }

    let currentPort = env.PORT;
    const server = app.listen(currentPort, () => {
      logger.info(`Jurist AI Backend Server listening on port ${currentPort} (${env.NODE_ENV} mode)`);
      logger.info(`Health check endpoint: http://localhost:${currentPort}/api/v1/health`);
    });

    server.on('error', (err: any) => {
      if (err.code === 'EADDRINUSE') {
        if (env.NODE_ENV === 'production') {
          logger.error(`[CRITICAL] Port ${currentPort} is already in use in production environment. Halting to avoid misrouting.`);
          process.exit(1);
        }
        logger.warn(`Port ${currentPort} is already in use (e.g. by macOS ControlCenter or AirPlay).`);
        currentPort++;
        logger.info(`Attempting to bind on alternate port ${currentPort}...`);
        server.listen(currentPort, () => {
          logger.info(`Jurist AI Backend Server listening on port ${currentPort} (${env.NODE_ENV} mode)`);
          logger.info(`Health check endpoint: http://localhost:${currentPort}/api/v1/health`);
        });
      } else {
        logger.error('Server listen error:', err.message);
      }
    });

    const shutdown = async () => {
      logger.info('Shutting down server gracefully...');
      server.close(() => {
        logger.info('HTTP server closed.');
        process.exit(0);
      });
    };

    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
  } catch (err: any) {
    logger.error('Failed to start server:', err.message);
    process.exit(1);
  }
};

if (process.env.NODE_ENV !== 'test') {
  startServer();
}
