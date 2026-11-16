import mongoose from 'mongoose';
import { Analysis } from '../models/Analysis';
import { Case } from '../models/Case';
import { mlClient } from '../integrations/mlClient';
import { getDBStatus } from '../config/db';
import { CaseService } from './caseService';
import { LegalArgumentService } from './argumentService';
import { LegislationService } from './legislationService';

const memoryAnalyses: Map<string, any> = new Map();

export class AnalysisService {
  public static async performAnalysis(
    userId: string,
    data: {
      caseId?: string;
      caseTitle?: string;
      description?: string;
      court?: string;
      category?: string;
      text?: string;
      documentMetadata?: any;
    }
  ) {
    let fullText = data.text || data.description || '';
    let title = data.caseTitle || 'Legal Dispute Research Memorandum';
    let court = data.court || 'Supreme Court of India';
    let category = data.category || 'General';

    if (data.caseId) {
      try {
        const caseRecord = await CaseService.getCaseById(userId, data.caseId);
        if (caseRecord) {
          title = caseRecord.title || title;
          court = caseRecord.court || court;
          category = caseRecord.category || category;

          const docTexts = (caseRecord.uploadedDocuments || [])
            .map((d: any) => d.extractedText || d.extractedTextSnippet || '')
            .filter((t: string) => t.length > 0)
            .join('\n\n');

          fullText = `${caseRecord.description || ''}\n\n${docTexts}`.trim();
        }
      } catch {
        // Proceed with directly supplied text if caseId lookup does not match
      }
    }

    if (!fullText || fullText.trim().length < 15) {
      throw new Error('Case description or extracted document text is too short for structured legal analysis.');
    }

    // 1. Date-aware legislation & transition determination (IPC/CrPC/IEA vs BNS/BNSS/BSA)
    const applicableLaw = LegislationService.assessApplicableLegislation(fullText, category);

    // 2. Attempt Python AI-Powered Legal Intelligence microservice
    const pyIntelligence = await mlClient.generateLegalIntelligence(
      fullText,
      category,
      court,
      data.documentMetadata,
      applicableLaw
    );

    let caseUnderstanding: any;
    let legalIssues: any[];
    let legalArguments: any[];
    let evidenceTraceGraph: any[];
    let matchedPrecedents: any[];
    let extractedEntities: any;
    let predictionResult: any;
    let citationGrounding: any = undefined;
    let generationMode: string = 'typescript_local_fallback';
    let llmModel: string | undefined = undefined;

    if (pyIntelligence && pyIntelligence.legalArguments && pyIntelligence.legalArguments.length > 0) {
      // Use Python ML service intelligence
      caseUnderstanding = pyIntelligence.caseUnderstanding;
      matchedPrecedents = pyIntelligence.precedents || [];
      extractedEntities = {
        ...(pyIntelligence.entities || {}),
        parties: caseUnderstanding.parties
      };
      legalIssues = pyIntelligence.questionsOfLaw || pyIntelligence.legalIssues || [];
      legalArguments = pyIntelligence.legalArguments;
      evidenceTraceGraph = pyIntelligence.evidenceTraceGraph || [];
      citationGrounding = pyIntelligence.citationGrounding;
      generationMode = pyIntelligence.generationMode || 'deterministic_offline';
      llmModel = pyIntelligence.llmModel;
      predictionResult = pyIntelligence.prediction;
    } else {
      // Fallback: Statutory entity extraction, issue matching, and verified precedent retrieval
      const mlResult = await mlClient.analyzeCase(fullText, category);
      matchedPrecedents = mlResult.precedents || [];

      // Strict fact classification, chronology, custody posture & evidence audit
      caseUnderstanding = LegalArgumentService.analyzeCaseFacts(
        fullText,
        category,
        court,
        applicableLaw,
        data.documentMetadata
      );

      // Structured Indian questions of law (merged cleanly with NLP rule signals without duplicates)
      const structuredQuestions = LegalArgumentService.buildQuestionsOfLaw(fullText, applicableLaw, caseUnderstanding);
      const seenIssues = new Set(structuredQuestions.map(q => q.issue.toLowerCase()));
      const additionalIssues = (mlResult.legalIssues || []).filter((iss: any) => {
        const key = (iss.issue || '').toLowerCase();
        if (seenIssues.has(key)) return false;
        seenIssues.add(key);
        return true;
      });
      legalIssues = [...structuredQuestions, ...additionalIssues];

      // Court-ready grounds, Article 141 ratio/obiter analysis, opposing counsel arguments & rebuttals
      legalArguments = LegalArgumentService.generateLegalArguments(
        fullText,
        category,
        court,
        matchedPrecedents,
        caseUnderstanding,
        applicableLaw
      );

      // Assemble Evidence Trace Graph
      evidenceTraceGraph = LegalArgumentService.buildEvidenceTraceGraph(
        caseUnderstanding,
        legalIssues,
        legalArguments,
        matchedPrecedents,
        applicableLaw,
        data.documentMetadata
      );

      extractedEntities = {
        ...(mlResult.entities || {}),
        parties: caseUnderstanding.parties
      };
      predictionResult = mlResult.prediction;
      generationMode = 'typescript_local_fallback';
    }

    // 6. Qualitative judicial treatment assessment (replacing misleading statistical win rates)
    const judicialTreatment = LegalArgumentService.buildJudicialTreatmentAssessment(
      fullText,
      matchedPrecedents,
      caseUnderstanding,
      applicableLaw
    );

    const dbStatus = getDBStatus();
    const isMongo = dbStatus.isConnected;

    const analysisPayload = {
      userId: isMongo && mongoose.Types.ObjectId.isValid(userId) ? new mongoose.Types.ObjectId(userId) : userId,
      caseId:
        data.caseId && isMongo && mongoose.Types.ObjectId.isValid(data.caseId)
          ? new mongoose.Types.ObjectId(data.caseId)
          : undefined,
      caseTitle: title,
      court,
      category,
      inputTextSnippet: fullText.slice(0, 800) + (fullText.length > 800 ? '...' : ''),
      caseUnderstanding,
      applicableLaw,
      extractedEntities,
      legalIssues,
      similarCases: matchedPrecedents,
      legalArguments,
      judicialTreatment,
      evidenceTraceGraph,
      citationGrounding,
      generationMode,
      llmModel,
      requiresAdvocateReview: true,
      prediction: predictionResult || {
        status: 'qualitative_research_mode',
        estimatedOutcome: 'Structured Doctrinal & Authority Assessment',
        rationale: judicialTreatment.researchScopeNote,
        disclaimer: 'Legal research output only. Not legal advice or a prediction of judicial outcomes.'
      },
      researchNotes: '',
      editedDrafts: {},
      documentMetadata: data.documentMetadata || null,
      processingStatus: 'completed' as const
    };

    if (isMongo) {
      const record = await Analysis.create(analysisPayload);

      if (data.caseId && mongoose.Types.ObjectId.isValid(data.caseId)) {
        await Case.findByIdAndUpdate(data.caseId, { status: 'analyzed' });
      }

      const obj = record.toObject();
      return {
        ...obj,
        persistenceMode: 'mongodb'
      };
    } else {
      const analysisId = 'an_' + Date.now();
      const mockRecord = {
        _id: analysisId,
        id: analysisId,
        ...analysisPayload,
        persistenceMode: 'in_memory_fallback',
        createdAt: new Date(),
        updatedAt: new Date()
      };
      memoryAnalyses.set(analysisId, mockRecord);
      return mockRecord;
    }
  }

  public static async getUserAnalyses(
    userId: string,
    options: { page?: number; limit?: number; search?: string; category?: string } = {}
  ) {
    const { page = 1, limit = 10, search, category } = options;
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const query: any = {
        userId: mongoose.Types.ObjectId.isValid(userId) ? new mongoose.Types.ObjectId(userId) : userId
      };

      if (category && category !== 'All') {
        query.category = category;
      }

      if (search) {
        query.$or = [
          { caseTitle: { $regex: search, $options: 'i' } },
          { inputTextSnippet: { $regex: search, $options: 'i' } }
        ];
      }

      const total = await Analysis.countDocuments(query);
      const records = await Analysis.find(query)
        .sort({ createdAt: -1 })
        .skip((page - 1) * limit)
        .limit(limit);

      return {
        analyses: records.map(r => ({ ...r.toObject(), persistenceMode: 'mongodb' })),
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
        persistenceMode: 'mongodb'
      };
    } else {
      let filtered = Array.from(memoryAnalyses.values()).filter(a => String(a.userId) === String(userId));

      if (category && category !== 'All') {
        filtered = filtered.filter(a => a.category === category);
      }

      if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(
          a => a.caseTitle.toLowerCase().includes(s) || a.inputTextSnippet.toLowerCase().includes(s)
        );
      }

      filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      const total = filtered.length;
      const paginated = filtered.slice((page - 1) * limit, page * limit);

      return {
        analyses: paginated,
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
        persistenceMode: 'in_memory_fallback'
      };
    }
  }

  public static async getAnalysisById(userId: string, analysisId: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      if (!mongoose.Types.ObjectId.isValid(analysisId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      const found = await Analysis.findOne({
        _id: new mongoose.Types.ObjectId(analysisId),
        userId: mongoose.Types.ObjectId.isValid(userId) ? new mongoose.Types.ObjectId(userId) : userId
      });
      if (!found) throw new Error('Analysis record not found or access denied.');
      return { ...found.toObject(), persistenceMode: 'mongodb' };
    } else {
      const found = memoryAnalyses.get(analysisId);
      if (!found || String(found.userId) !== String(userId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      return found;
    }
  }

  public static async updateAnalysis(
    userId: string,
    analysisId: string,
    updates: {
      researchNotes?: string;
      editedDrafts?: Record<string, string>;
      caseTitle?: string;
    }
  ) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      if (!mongoose.Types.ObjectId.isValid(analysisId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      const existing = await Analysis.findOne({
        _id: new mongoose.Types.ObjectId(analysisId),
        userId: mongoose.Types.ObjectId.isValid(userId) ? new mongoose.Types.ObjectId(userId) : userId
      });
      if (!existing) throw new Error('Analysis record not found or access denied.');

      if (typeof updates.researchNotes === 'string') {
        existing.researchNotes = updates.researchNotes;
      }
      if (typeof updates.caseTitle === 'string' && updates.caseTitle.trim().length >= 3) {
        existing.caseTitle = updates.caseTitle.trim();
      }
      if (updates.editedDrafts && typeof updates.editedDrafts === 'object') {
        existing.editedDrafts = {
          ...(existing.editedDrafts || {}),
          ...updates.editedDrafts
        };
        existing.markModified('editedDrafts');
      }

      await existing.save();
      return { ...existing.toObject(), persistenceMode: 'mongodb' };
    } else {
      const found = memoryAnalyses.get(analysisId);
      if (!found || String(found.userId) !== String(userId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      const nextRecord = {
        ...found,
        ...(typeof updates.researchNotes === 'string' ? { researchNotes: updates.researchNotes } : {}),
        ...(typeof updates.caseTitle === 'string' && updates.caseTitle.trim().length >= 3
          ? { caseTitle: updates.caseTitle.trim() }
          : {}),
        ...(updates.editedDrafts
          ? { editedDrafts: { ...(found.editedDrafts || {}), ...updates.editedDrafts } }
          : {}),
        updatedAt: new Date()
      };
      memoryAnalyses.set(analysisId, nextRecord);
      return nextRecord;
    }
  }

  public static async deleteAnalysis(userId: string, analysisId: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      if (!mongoose.Types.ObjectId.isValid(analysisId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      const res = await Analysis.findOneAndDelete({
        _id: new mongoose.Types.ObjectId(analysisId),
        userId: mongoose.Types.ObjectId.isValid(userId) ? new mongoose.Types.ObjectId(userId) : userId
      });
      if (!res) throw new Error('Analysis record not found or access denied.');
      return true;
    } else {
      const found = memoryAnalyses.get(analysisId);
      if (!found || String(found.userId) !== String(userId)) {
        throw new Error('Analysis record not found or access denied.');
      }
      memoryAnalyses.delete(analysisId);
      return true;
    }
  }
}
