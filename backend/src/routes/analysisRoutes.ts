import { Router } from 'express';
import { AnalysisController } from '../controllers/analysisController';
import { requireAuth } from '../middleware/auth';
import { uploadMiddleware } from '../middleware/upload';
import { validateRequest } from '../middleware/validate';
import { updateAnalysisSchema } from '../validators/analysisSchemas';

const router = Router();

router.use(requireAuth);

router.post('/', uploadMiddleware.single('document'), AnalysisController.createAnalysis);
router.get('/', AnalysisController.getAnalyses);
router.get('/:id', AnalysisController.getAnalysisById);
router.patch('/:id', validateRequest(updateAnalysisSchema), AnalysisController.updateAnalysis);
router.delete('/:id', AnalysisController.deleteAnalysis);

export default router;
