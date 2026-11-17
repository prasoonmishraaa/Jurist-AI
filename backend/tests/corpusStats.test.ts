import { getCorpusStatistics } from '../src/utils/corpusStats';
import { judgmentRegistry } from '../src/utils/judgmentRegistry';

describe('CorpusStatistics Verification & Dual-Store Audit', () => {
  it('correctly resolves hybrid retrieval corpus count as 176 unique judgments', async () => {
    const stats = await getCorpusStatistics();
    expect(stats.totalJudgments).toBe(176);
  });

  it('correctly reports 771 indexed passages across the semantic hybrid index', async () => {
    const stats = await getCorpusStatistics();
    expect(stats.indexedPassages).toBe(771);
  });

  it('accurately resolves landmark source verification: 10 official verified and 17 secondary references', async () => {
    const stats = await getCorpusStatistics();
    expect(stats.landmarkJudgments).toBe(27);
    expect(stats.officialVerifiedLandmarks).toBe(10);
    expect(stats.secondaryReferences).toBe(17);
    expect(stats.officialVerifiedLandmarks + stats.secondaryReferences).toBe(stats.landmarkJudgments);
  });

  it('accurately resolves 149 Open India Law judgments (deduplicated)', async () => {
    const stats = await getCorpusStatistics();
    expect(stats.openIndiaLawJudgments).toBe(149);
    expect(stats.landmarkJudgments + stats.openIndiaLawJudgments).toBe(stats.totalJudgments);
  });

  it('strictly distinguishes MongoDB synchronized records (27) from ML hybrid retrieval corpus (176)', async () => {
    const stats = await getCorpusStatistics();
    expect(stats.databaseSyncedRecords).toBe(27);
    expect(stats.totalJudgments).toBe(176);
    expect(stats.databaseSyncedRecords).not.toBe(stats.totalJudgments);
  });
});
