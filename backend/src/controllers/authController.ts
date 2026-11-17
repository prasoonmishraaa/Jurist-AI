import { Request, Response } from 'express';
import { AuthService } from '../services/authService';
import { sendSuccess, sendError } from '../utils/apiResponse';
import { AuthRequest } from '../middleware/auth';

export class AuthController {
  public static async register(req: Request, res: Response) {
    try {
      const { name, email, password } = req.body;
      const result = await AuthService.register(name, email, password, 'user');
      return sendSuccess(res, result, 'User registered successfully.', 201);
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async login(req: Request, res: Response) {
    try {
      const { email, password } = req.body;
      const result = await AuthService.login(email, password);
      return sendSuccess(res, result, 'Login successful.');
    } catch (err: any) {
      return sendError(res, err.message, 401);
    }
  }

  public static async logout(req: Request, res: Response) {
    return sendSuccess(res, null, 'Logged out successfully.');
  }

  public static async me(req: AuthRequest, res: Response) {
    try {
      if (!req.user) {
        return sendError(res, 'Unauthorized', 401);
      }
      const user = await AuthService.getUserById(req.user.id);
      return sendSuccess(res, user, 'Profile retrieved successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 404);
    }
  }
}
