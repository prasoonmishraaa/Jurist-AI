import { Request, Response, NextFunction } from 'express';
import multer from 'multer';
import { env } from '../config/env';
import { logger } from '../utils/logger';
import { sendError } from '../utils/apiResponse';

export const errorHandler = (
  err: any,
  req: Request,
  res: Response,
  _next: NextFunction
) => {
  logger.error(`Request failure in [${req.method}] ${req.originalUrl}: ${err.message}`);

  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return sendError(
        res,
        `Uploaded file exceeds the maximum permitted limit of ${env.MAX_FILE_SIZE_MB} MB.`,
        400
      );
    }
    return sendError(res, `Upload error: ${err.message}`, 400);
  }

  if (
    typeof err.message === 'string' &&
    (err.message.startsWith('Unsupported file type') ||
      err.message.startsWith('File MIME type') ||
      err.message.startsWith('Invalid document format'))
  ) {
    return sendError(res, err.message, 400);
  }

  if (err.name === 'ValidationError') {
    return sendError(res, err.message, 400);
  }

  if (err.code === 11000) {
    return sendError(res, 'Duplicate record detected. This item already exists.', 409);
  }

  if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
    return sendError(res, 'Authentication token is invalid or expired.', 401);
  }

  const statusCode = err.statusCode || 500;
  const message =
    process.env.NODE_ENV === 'production' && statusCode === 500
      ? 'An unexpected internal server error occurred.'
      : err.message || 'Internal server error';

  return sendError(res, message, statusCode);
};
