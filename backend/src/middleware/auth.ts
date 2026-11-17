import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { env } from '../config/env';
import { sendError } from '../utils/apiResponse';
import { User, IUser } from '../models/User';

export interface AuthRequest extends Request {
  user?: {
    id: string;
    email: string;
    role: 'user' | 'admin';
    name: string;
  };
}

export const requireAuth = async (req: AuthRequest, res: Response, next: NextFunction) => {
  try {
    let token: string | undefined;

    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer ')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      return sendError(res, 'Authentication required. Please provide a valid Bearer token.', 401);
    }

    if (!env.JWT_SECRET) {
      return sendError(res, 'Server authentication configuration is incomplete.', 503);
    }

    const decoded = jwt.verify(token, env.JWT_SECRET) as { id: string; email: string; role: 'user' | 'admin'; name: string };
    req.user = decoded;
    return next();
  } catch (err: any) {
    return sendError(res, 'Invalid or expired authentication token. Please log in again.', 401);
  }
};

export const requireAdmin = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (!req.user || req.user.role !== 'admin') {
    return sendError(res, 'Access denied. Administrator privileges required.', 403);
  }
  return next();
};
