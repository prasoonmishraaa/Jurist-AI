import { Precedent } from './models/Precedent';
import { connectDB, getDBStatus, disconnectDB } from './config/db';
import { logger } from './utils/logger';
import { judgmentRegistry } from './utils/judgmentRegistry';

export const seedPrecedents = async (forceUpsert = false) => {
  try {
    const dbStatus = getDBStatus();
    if (!dbStatus.isConnected) {
      logger.info('Database disconnected; skipping database seed.');
      return;
    }

    const judgments = judgmentRegistry.getAll();
    if (judgments.length === 0) {
      logger.warn('Judgment registry empty; nothing to seed.');
      return;
    }

    const existingCount = await Precedent.countDocuments();
    if (existingCount >= judgments.length && !forceUpsert) {
      // Refresh source metadata safely via bulk upsert by citation/precedentCode
      logger.info(`Synchronizing ${judgments.length} verified judgment records in MongoDB.`);
    }

    for (const item of judgments) {
      await Precedent.findOneAndUpdate(
        { $or: [{ precedentCode: item.id }, { citation: item.citation }] },
        {
          precedentCode: item.id,
          caseTitle: item.caseTitle,
          court: item.court,
          judgmentDate: item.judgmentDate,
          caseIdentifier: item.caseIdentifier,
          citation: item.citation,
          bench: item.bench,
          category: item.category,
          legalProvisions: item.legalProvisions,
          summary: item.summary,
          judgmentText: item.judgmentText,
          officialSourceUrl: item.officialSourceUrl || '',
          officialSourceLabel: item.officialSourceLabel || '',
          officialSourceVerified: Boolean(item.officialSourceVerified),
          secondaryReferenceUrl: item.secondaryReferenceUrl || '',
          secondaryReferenceLabel: item.secondaryReferenceLabel || '',
          sourceUrl: item.sourceUrl || '',
          verificationStatus: item.verificationStatus || 'secondary_verified_official_unverified',
          verificationNote: item.verificationNote || '',
          article141Status: item.article141Status || '',
          obiterAndScopeNote: item.obiterAndScopeNote || '',
          subsequentTreatment: item.subsequentTreatment || '',
          outcome: item.outcome,
          outcomeRationale: item.outcomeRationale
        },
        { upsert: true, new: true }
      );
    }

    logger.info(`Successfully synchronized ${judgments.length} verified Indian court precedents in MongoDB.`);
  } catch (err: any) {
    logger.error('Error during precedent seeding:', err.message);
  }
};

// Standalone execution support
if (require.main === module) {
  (async () => {
    await connectDB();
    await seedPrecedents(true);
    await disconnectDB();
    process.exit(0);
  })();
}
