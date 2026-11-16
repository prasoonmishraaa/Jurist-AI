import { Request, Response, NextFunction } from 'express';
import { AnyZodObject, ZodError } from 'zod';
import { sendError } from '../utils/apiResponse';

export const validateRequest = (schema: AnyZodObject) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      await schema.parseAsync({
        body: req.body,
        query: req.query,
        params: req.params
      });
      return next();
    } catch (error) {
      if (error instanceof ZodError) {
        const errorMessages = error.errors.map(err => `${err.path.join('.')}: ${err.message}`).join(', ');
        return sendError(res, `Validation error: ${errorMessages}`, 400);
      }
      return sendError(res, 'Internal validation failure.', 500);
    }
  };
};
