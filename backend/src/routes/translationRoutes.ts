import { Router } from 'express';
import { TranslationController } from '../controllers/translationController';
import { requireAuth } from '../middleware/auth';

const router = Router();

// Protect translation endpoints with authentication
router.use(requireAuth);

router.post('/detect-language', TranslationController.detectLanguage);
router.post('/translate', TranslationController.translate);

export default router;
