import { Router } from 'express';
import { UserController } from '../controllers/userController';
import { requireAuth } from '../middleware/auth';
import { validateRequest } from '../middleware/validate';
import { updateProfileSchema, updatePasswordSchema } from '../validators/authSchemas';

const router = Router();

router.use(requireAuth);

router.get('/me', UserController.getMe);
router.patch('/me', validateRequest(updateProfileSchema), UserController.updateMe);
router.patch('/me/password', validateRequest(updatePasswordSchema), UserController.updatePassword);

export default router;
