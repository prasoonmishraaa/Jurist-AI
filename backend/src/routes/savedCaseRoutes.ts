import { Router } from 'express';
import { SavedCaseController } from '../controllers/savedCaseController';
import { requireAuth } from '../middleware/auth';

const router = Router();

router.use(requireAuth);

router.post('/', SavedCaseController.saveCase);
router.get('/', SavedCaseController.getSavedCases);
router.patch('/:id', SavedCaseController.updateSavedCase);
router.delete('/:id', SavedCaseController.deleteSavedCase);

export default router;
