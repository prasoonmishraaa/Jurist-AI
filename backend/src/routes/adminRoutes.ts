import { Router } from 'express';
import { AdminController } from '../controllers/adminController';
import { requireAuth, requireAdmin } from '../middleware/auth';

const router = Router();

router.use(requireAuth, requireAdmin);

router.get('/users', AdminController.getUsers);
router.get('/stats', AdminController.getStats);

export default router;
