import mongoose from 'mongoose';
import { env } from './env';
import { logger } from '../utils/logger';

let connectPromise: Promise<boolean> | null = null;

export const connectDB = async (): Promise<boolean> => {
  if (mongoose.connection.readyState === 1) {
    return true;
  }

  if (connectPromise) {
    return connectPromise;
  }

  if (!env.MONGODB_URI) {
    logger.warn('MONGODB_URI is not set. Running with non-persistent in-memory session storage.');
    return false;
  }

  connectPromise = (async () => {
    try {
      const conn = await mongoose.connect(env.MONGODB_URI, {
        serverSelectionTimeoutMS: 5000,
        autoIndex: true
      });
      const ready = conn.connections[0].readyState === 1;
      logger.info(`MongoDB connected to host: ${conn.connection.host}`);
      return ready;
    } catch (error: any) {
      logger.error('Failed to connect to MongoDB:', error.message);
      logger.warn('Continuing with non-persistent in-memory session storage.');
      return false;
    } finally {
      connectPromise = null;
    }
  })();

  return connectPromise;
};

export const getDBStatus = () => {
  const readyState = mongoose.connection.readyState;
  const isConnected = readyState === 1;
  return {
    isConnected,
    state: readyState,
    persistenceMode: isConnected ? ('mongodb' as const) : ('in_memory_fallback' as const),
    host: isConnected ? mongoose.connection.host : 'in-memory-session-store'
  };
};

export const disconnectDB = async () => {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
  }
};
