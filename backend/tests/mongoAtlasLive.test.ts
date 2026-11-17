import mongoose from 'mongoose';
import { env } from '../src/config/env';
import { connectDB, disconnectDB, getDBStatus } from '../src/config/db';
import { AnalysisService } from '../src/services/analysisService';
import { Analysis } from '../src/models/Analysis';

describe('MongoDB Atlas Live Verification & Isolation Suite', () => {
  const userAId = new mongoose.Types.ObjectId().toString();
  const userBId = new mongoose.Types.ObjectId().toString();
  let createdAnalysisId: string = '';

  beforeAll(async () => {
    // Explicitly connect to MongoDB Atlas cluster
    const connected = await connectDB();
    if (!connected) {
      console.warn('Could not connect to MongoDB Atlas. Live tests will reflect actual state.');
    }
  }, 15000);

  afterAll(async () => {
    // Clean up any test records created
    try {
      if (mongoose.connection.readyState === 1) {
        if (createdAnalysisId && mongoose.Types.ObjectId.isValid(createdAnalysisId)) {
          await Analysis.deleteOne({ _id: new mongoose.Types.ObjectId(createdAnalysisId) });
        }
        await Analysis.deleteMany({ userId: { $in: [new mongoose.Types.ObjectId(userAId), new mongoose.Types.ObjectId(userBId)] } });
      }
    } catch {
      // ignore cleanup errors
    } finally {
      await disconnectDB();
    }
  });

  it('1. verifies live connection to MongoDB Atlas and reports persistenceMode: mongodb', async () => {
    expect(env.MONGODB_URI).toBeDefined();
    expect(env.MONGODB_URI).toContain('mongodb+srv://');

    const dbStatus = getDBStatus();
    expect(dbStatus.isConnected).toBe(true);
    expect(dbStatus.persistenceMode).toBe('mongodb');
    expect(dbStatus.host).toContain('mongodb.net');
  });

  it('2. creates, retrieves, and validates an analysis record in MongoDB Atlas', async () => {
    const payload = {
      caseTitle: 'Atlas Verification — Criminal Custody Remand',
      court: 'Supreme Court of India',
      category: 'Criminal Law',
      description: 'The petitioner was arrested on 14 October 2024 without written grounds of arrest prior to remand under Section 47 BNSS.'
    };

    const created = await AnalysisService.performAnalysis(userAId, payload);
    expect(created).toBeDefined();
    expect(created.persistenceMode).toBe('mongodb');
    expect(created._id).toBeDefined();
    createdAnalysisId = created._id.toString();

    // Verify record exists in MongoDB collection
    const retrieved = await AnalysisService.getAnalysisById(userAId, createdAnalysisId);
    expect(retrieved).toBeDefined();
    expect(retrieved.caseTitle).toBe('Atlas Verification — Criminal Custody Remand');
    expect(retrieved.persistenceMode).toBe('mongodb');
    expect(retrieved.userId.toString()).toBe(userAId);
  });

  it('3. enforces strict user-level data isolation in MongoDB Atlas queries', async () => {
    expect(createdAnalysisId).toBeTruthy();

    // User B attempts to read User A's record by ID -> must fail
    await expect(AnalysisService.getAnalysisById(userBId, createdAnalysisId)).rejects.toThrow(
      'Analysis record not found or access denied.'
    );

    // User B lists their analyses -> User A's record must NOT be present
    const userBList = await AnalysisService.getUserAnalyses(userBId);
    expect(userBList.persistenceMode).toBe('mongodb');
    expect(userBList.total).toBe(0);
    const foundInB = userBList.analyses.some((a: any) => a._id.toString() === createdAnalysisId);
    expect(foundInB).toBe(false);

    // User B attempts to update User A's record -> must fail
    await expect(
      AnalysisService.updateAnalysis(userBId, createdAnalysisId, { researchNotes: 'Tamper attempt' })
    ).rejects.toThrow('Analysis record not found or access denied.');

    // User B attempts to delete User A's record -> must fail
    await expect(AnalysisService.deleteAnalysis(userBId, createdAnalysisId)).rejects.toThrow(
      'Analysis record not found or access denied.'
    );
  });

  it('4. updates analysis record and persists modifications to MongoDB Atlas', async () => {
    expect(createdAnalysisId).toBeTruthy();

    const updated = await AnalysisService.updateAnalysis(userAId, createdAnalysisId, {
      researchNotes: 'Chamber note: Inspect General Diary entries for arrest timestamp.',
      editedDrafts: { 'ground-1': 'Court submission drafted and verified.' },
      caseTitle: 'Atlas Verification — Modified Case Title'
    });

    expect(updated.persistenceMode).toBe('mongodb');
    expect(updated.researchNotes).toBe('Chamber note: Inspect General Diary entries for arrest timestamp.');
    expect(updated.editedDrafts['ground-1']).toBe('Court submission drafted and verified.');
    expect(updated.caseTitle).toBe('Atlas Verification — Modified Case Title');

    // Confirm direct MongoDB document state
    const directDoc = await Analysis.findById(new mongoose.Types.ObjectId(createdAnalysisId));
    expect(directDoc).not.toBeNull();
    expect(directDoc!.researchNotes).toBe('Chamber note: Inspect General Diary entries for arrest timestamp.');
    expect(directDoc!.caseTitle).toBe('Atlas Verification — Modified Case Title');
  });

  it('5. verifies records survive simulated application restart (disconnect & reconnect)', async () => {
    expect(createdAnalysisId).toBeTruthy();

    // Simulate application restart by fully disconnecting
    await mongoose.disconnect();
    expect(mongoose.connection.readyState).toBe(0);

    // Re-establish fresh connection to MongoDB Atlas
    const reconnected = await connectDB();
    expect(reconnected).toBe(true);
    expect(getDBStatus().persistenceMode).toBe('mongodb');

    // Fetch the record again from the fresh connection
    const persistentRecord = await AnalysisService.getAnalysisById(userAId, createdAnalysisId);
    expect(persistentRecord).toBeDefined();
    expect(persistentRecord.persistenceMode).toBe('mongodb');
    expect(persistentRecord.caseTitle).toBe('Atlas Verification — Modified Case Title');
    expect(persistentRecord.researchNotes).toBe('Chamber note: Inspect General Diary entries for arrest timestamp.');
    expect(persistentRecord.editedDrafts['ground-1']).toBe('Court submission drafted and verified.');
  }, 20000);

  it('6. deletes analysis record from MongoDB Atlas and confirms removal', async () => {
    expect(createdAnalysisId).toBeTruthy();

    const deleted = await AnalysisService.deleteAnalysis(userAId, createdAnalysisId);
    expect(deleted).toBe(true);

    // User A can no longer retrieve the deleted record
    await expect(AnalysisService.getAnalysisById(userAId, createdAnalysisId)).rejects.toThrow(
      'Analysis record not found or access denied.'
    );

    // Confirm removal in direct collection query
    const directDoc = await Analysis.findById(new mongoose.Types.ObjectId(createdAnalysisId));
    expect(directDoc).toBeNull();
  }, 20000);
});
