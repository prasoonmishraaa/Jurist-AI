import { Response } from 'express';

export interface ApiResponseData<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
  pagination?: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
    persistenceMode?: string;
  };
}

export const sendSuccess = <T>(
  res: Response,
  data?: T,
  message?: string,
  statusCode = 200,
  pagination?: ApiResponseData<T>['pagination']
) => {
  return res.status(statusCode).json({
    success: true,
    message,
    data,
    pagination
  });
};

export const sendError = (
  res: Response,
  error: string,
  statusCode = 400
) => {
  return res.status(statusCode).json({
    success: false,
    error
  });
};
