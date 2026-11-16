import { Router } from 'express';
import authRoutes from './authRoutes';
import userRoutes from './userRoutes';
import caseRoutes from './caseRoutes';
import analysisRoutes from './analysisRoutes';
import precedentRoutes from './precedentRoutes';
import savedCaseRoutes from './savedCaseRoutes';
import adminRoutes from './adminRoutes';
import translationRoutes from './translationRoutes';
import { getDBStatus } from '../config/db';
import { mlClient } from '../integrations/mlClient';
import { judgmentRegistry } from '../utils/judgmentRegistry';
import { getCorpusStatistics } from '../utils/corpusStats';
import { sendSuccess } from '../utils/apiResponse';

const router = Router();

router.get('/health', async (_req, res) => {
  const dbStatus = getDBStatus();
  const mlHealth = await mlClient.getHealth();
  const corpusStats = await getCorpusStatistics();

  return sendSuccess(
    res,
    {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      service: 'Jurist AI Research API',
      version: '2.0.0',
      persistenceMode: dbStatus.persistenceMode,
      database: dbStatus,
      verifiedPrecedentCount: corpusStats.totalJudgments,
      landmarkPrecedentCount: corpusStats.landmarkJudgments,
      databaseSyncedPrecedentCount: corpusStats.databaseSyncedRecords,
      indexedPassagesCount: corpusStats.indexedPassages,
      corpusStats,
      mlService: mlHealth
    },
    'Jurist AI system is operating normally.'
  );
});

router.use('/auth', authRoutes);
router.use('/users', userRoutes);
router.use('/cases', caseRoutes);
router.use('/analysis', analysisRoutes);
router.use('/precedents', precedentRoutes);
router.use('/saved-cases', savedCaseRoutes);
router.use('/admin', adminRoutes);
router.use('/translation', translationRoutes);

export default router;
