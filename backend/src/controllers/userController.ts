import { Response } from 'express';
import { AuthRequest } from '../middleware/auth';
import { AuthService } from '../services/authService';
import { sendSuccess, sendError } from '../utils/apiResponse';

export class UserController {
  public static async getMe(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const user = await AuthService.getUserById(req.user.id);
      return sendSuccess(res, user, 'Profile retrieved.');
    } catch (err: any) {
      return sendError(res, err.message, 404);
    }
  }

  public static async updateMe(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const { name } = req.body;
      const updated = await AuthService.updateProfile(req.user.id, name);
      return sendSuccess(res, updated, 'Profile updated successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async updatePassword(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const { currentPassword, newPassword } = req.body;
      await AuthService.updatePassword(req.user.id, currentPassword, newPassword);
      return sendSuccess(res, null, 'Password updated successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }
}
