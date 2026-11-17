import { Router } from 'express';
import { PrecedentController } from '../controllers/precedentController';

const router = Router();

// Precedents can be viewed publicly or authenticated
router.get('/', PrecedentController.getPrecedents);
router.get('/stats', PrecedentController.getCorpusStats);
router.get('/:id', PrecedentController.getPrecedentById);

export default router;
