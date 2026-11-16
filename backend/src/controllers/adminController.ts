import { Response } from 'express';
import { AuthRequest } from '../middleware/auth';
import { User } from '../models/User';
import { Case } from '../models/Case';
import { Analysis } from '../models/Analysis';
import { Precedent } from '../models/Precedent';
import { getDBStatus } from '../config/db';
import { mlClient } from '../integrations/mlClient';
import { judgmentRegistry } from '../utils/judgmentRegistry';
import { getCorpusStatistics } from '../utils/corpusStats';
import { sendSuccess, sendError } from '../utils/apiResponse';

export class AdminController {
  public static async getUsers(req: AuthRequest, res: Response) {
    try {
      const dbStatus = getDBStatus();
      if (dbStatus.isConnected) {
        const users = await User.find().select('-passwordHash').sort({ createdAt: -1 });
        return sendSuccess(res, users, 'Users retrieved.');
      } else {
        return sendSuccess(
          res,
          [{ id: req.user?.id, name: req.user?.name, email: req.user?.email, role: req.user?.role, createdAt: new Date() }],
          'Users retrieved (non-persistent session store).'
        );
      }
    } catch (err: any) {
      return sendError(res, err.message, 500);
    }
  }

  public static async getStats(_req: AuthRequest, res: Response) {
    try {
      const dbStatus = getDBStatus();
      const mlHealth = await mlClient.getHealth();
      const corpusStats = await getCorpusStatistics();
      const registryRecords = judgmentRegistry.getAll();

      if (dbStatus.isConnected) {
        const [userCount, caseCount, analysisCount, precedentCount] = await Promise.all([
          User.countDocuments(),
          Case.countDocuments(),
          Analysis.countDocuments(),
          Precedent.countDocuments()
        ]);

        return sendSuccess(
          res,
          {
            totalUsers: userCount,
            totalCases: caseCount,
            totalAnalyses: analysisCount,
            precedentCorpusCount: corpusStats.totalJudgments,
            hybridCorpusCount: corpusStats.totalJudgments,
            indexedPassages: corpusStats.indexedPassages,
            officialVerifiedSourceCount: corpusStats.officialVerifiedLandmarks,
            secondaryReferenceCount: corpusStats.secondaryReferences,
            openIndiaLawCount: corpusStats.openIndiaLawJudgments,
            databaseSyncedCount: precedentCount || corpusStats.databaseSyncedRecords,
            corpusStats,
            persistenceMode: dbStatus.persistenceMode,
            database: dbStatus,
            mlService: mlHealth
          },
          'System statistics retrieved.'
        );
      } else {
        return sendSuccess(
          res,
          {
            totalUsers: 1,
            totalCases: 0,
            totalAnalyses: 0,
            precedentCorpusCount: corpusStats.totalJudgments,
            hybridCorpusCount: corpusStats.totalJudgments,
            indexedPassages: corpusStats.indexedPassages,
            officialVerifiedSourceCount: corpusStats.officialVerifiedLandmarks,
            secondaryReferenceCount: corpusStats.secondaryReferences,
            openIndiaLawCount: corpusStats.openIndiaLawJudgments,
            databaseSyncedCount: registryRecords.length,
            corpusStats,
            persistenceMode: dbStatus.persistenceMode,
            database: dbStatus,
            mlService: mlHealth
          },
          'System statistics retrieved.'
        );
      }
    } catch (err: any) {
      return sendError(res, err.message, 500);
    }
  }
}
