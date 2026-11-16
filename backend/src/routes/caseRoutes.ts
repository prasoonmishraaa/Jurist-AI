import { Router } from 'express';
import { CaseController } from '../controllers/caseController';
import { requireAuth } from '../middleware/auth';
import { uploadMiddleware } from '../middleware/upload';

const router = Router();

router.use(requireAuth);

router.post('/', uploadMiddleware.single('document'), CaseController.createCase);
router.get('/', CaseController.getCases);
router.get('/:id', CaseController.getCaseById);
router.delete('/:id', CaseController.deleteCase);

export default router;
