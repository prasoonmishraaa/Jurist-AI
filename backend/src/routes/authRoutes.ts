import { Router } from 'express';
import { AuthController } from '../controllers/authController';
import { validateRequest } from '../middleware/validate';
import { registerSchema, loginSchema } from '../validators/authSchemas';
import { authRateLimiter } from '../middleware/rateLimiter';
import { requireAuth } from '../middleware/auth';

const router = Router();

router.post('/register', authRateLimiter, validateRequest(registerSchema), AuthController.register);
router.post('/login', authRateLimiter, validateRequest(loginSchema), AuthController.login);
router.post('/logout', AuthController.logout);
router.get('/me', requireAuth, AuthController.me);

export default router;
