import axios from 'axios';
import { env } from '../config/env';
import { logger } from '../utils/logger';
import { localInferenceEngine } from './localInference';
import { judgmentRegistry } from '../utils/judgmentRegistry';

export class MLServiceClient {
  private baseUrl: string;
  private secret: string;

  constructor() {
    this.baseUrl = env.ML_SERVICE_URL;
    this.secret = env.INTERNAL_ML_SECRET;
  }

  private enrichPrecedents(precedents: any[]): any[] {
    return (precedents || []).map((p: any) => {
      const reg = judgmentRegistry.findById(p.id || '') || judgmentRegistry.findByKeyword(p.caseTitle || '');
      if (!reg) return p;
      return {
        ...p,
        id: reg.id,
        caseTitle: reg.caseTitle,
        court: reg.court,
        judgmentDate: reg.judgmentDate,
        citation: reg.citation,
        bench: reg.bench,
        category: reg.category,
        legalProvisions: reg.legalProvisions,
        officialSourceUrl: reg.officialSourceUrl,
        officialSourceLabel: reg.officialSourceLabel,
        officialSourceVerified: reg.officialSourceVerified,
        secondaryReferenceUrl: reg.secondaryReferenceUrl,
        secondaryReferenceLabel: reg.secondaryReferenceLabel,
        sourceUrl: reg.sourceUrl,
        verificationStatus: reg.verificationStatus,
        verificationNote: reg.verificationNote,
        article141Status: reg.article141Status,
        obiterAndScopeNote: reg.obiterAndScopeNote,
        subsequentTreatment: reg.subsequentTreatment
      };
    });
  }

  public async analyzeCase(text: string, category?: string): Promise<any> {
    if (this.baseUrl && !this.baseUrl.includes('undefined')) {
      try {
        const response = await axios.post(
          `${this.baseUrl}/api/ml/analyze`,
          { text, category },
          {
            headers: {
              'Content-Type': 'application/json',
              'x-internal-secret': this.secret
            },
            timeout: 25000
          }
        );
        if (response.data) {
          logger.info('Analysis executed via Python NLP service.');

          // Prefer valid Python hybrid retrieval results when returned
          const pythonPrecedents =
            Array.isArray(response.data.precedents) && response.data.precedents.length > 0
              ? this.enrichPrecedents(response.data.precedents)
              : [];

          // Use TypeScript local inference only if Python returned no usable precedents
          const finalPrecedents =
            pythonPrecedents.length > 0
              ? pythonPrecedents
              : localInferenceEngine.retrieveSimilarPrecedents(text, 6);

          return {
            ...response.data,
            precedents: finalPrecedents,
            prediction: response.data.prediction || localInferenceEngine.predictOutcome(text, category)
          };
        }
      } catch (err: any) {
        logger.info(`Python NLP service unavailable (${err.message}); using built-in statutory & precedent engine.`);
      }
    }

    const entities = localInferenceEngine.extractEntities(text);
    const legalIssues = localInferenceEngine.identifyIssues(text);
    const precedents = localInferenceEngine.retrieveSimilarPrecedents(text, 6);
    const prediction = localInferenceEngine.predictOutcome(text, category);

    return {
      cleanedTextSnippet: text.slice(0, 300) + (text.length > 300 ? '...' : ''),
      entities,
      legalIssues,
      precedents,
      prediction
    };
  }

  public async generateLegalIntelligence(
    text: string,
    category?: string,
    court?: string,
    documentMetadata?: any,
    applicableLaw?: any
  ): Promise<any> {
    if (this.baseUrl && !this.baseUrl.includes('undefined')) {
      try {
        const response = await axios.post(
          `${this.baseUrl}/api/ml/legal-intelligence`,
          {
            text,
            category,
            court,
            documentMetadata,
            applicableLaw
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'x-internal-secret': this.secret
            },
            timeout: 30000
          }
        );

        if (response.data && response.data.legalArguments) {
          logger.info(`Legal intelligence generated via Python service (mode: ${response.data.generationMode || 'unknown'}).`);

          const pythonPrecedents =
            Array.isArray(response.data.precedents) && response.data.precedents.length > 0
              ? this.enrichPrecedents(response.data.precedents)
              : [];

          return {
            ...response.data,
            precedents: pythonPrecedents.length > 0 ? pythonPrecedents : localInferenceEngine.retrieveSimilarPrecedents(text, 6)
          };
        }
      } catch (err: any) {
        logger.info(`Python legal intelligence endpoint unavailable (${err.message}); utilizing Node.js legal argument engine.`);
      }
    }

    return null;
  }

  public async retrieveSimilar(text: string, topK = 5): Promise<any[]> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/ml/similarity`,
        { text, top_k: topK },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-internal-secret': this.secret
          },
          timeout: 15000
        }
      );
      if (response.data?.precedents) {
        return this.enrichPrecedents(response.data.precedents);
      }
    } catch {
      // fallback below
    }

    return localInferenceEngine.retrieveSimilarPrecedents(text, topK);
  }

  public async predictOutcome(text: string, category?: string, maxSimilarity = 0.5): Promise<any> {
    if (this.baseUrl && !this.baseUrl.includes('undefined')) {
      try {
        const response = await axios.post(
          `${this.baseUrl}/api/ml/predict`,
          { text, category, max_similarity: maxSimilarity },
          {
            headers: {
              'Content-Type': 'application/json',
              'x-internal-secret': this.secret
            },
            timeout: 10000
          }
        );
        if (response.data?.prediction) {
          return response.data.prediction;
        }
      } catch {
        // Fall back to local inference engine below
      }
    }
    return localInferenceEngine.predictOutcome(text, category, maxSimilarity);
  }

  public async extractDocument(
    buffer: Buffer,
    filename: string,
    mimeType: string
  ): Promise<any> {
    if (!this.baseUrl || this.baseUrl.includes('undefined')) {
      throw new Error('Python ML microservice URL is not configured.');
    }

    const payload = {
      fileBase64: buffer.toString('base64'),
      filename,
      mimeType
    };

    const response = await axios.post(
      `${this.baseUrl}/api/ml/extract-document`,
      payload,
      {
        headers: {
          'Content-Type': 'application/json',
          'x-internal-secret': this.secret
        },
        timeout: env.DOCUMENT_EXTRACTION_TIMEOUT_MS || 60000
      }
    );

    return response.data;
  }

  public async getHealth(): Promise<any> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/ml/health`, { timeout: 1500 });
      return { pythonService: response.data, localEngine: 'active' };
    } catch {
      return { pythonService: 'offline / serverless mode', localEngine: 'active' };
    }
  }
}

export const mlClient = new MLServiceClient();
