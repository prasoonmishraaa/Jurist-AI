import { Response } from 'express';
import { AuthRequest } from '../middleware/auth';
import { AnalysisService } from '../services/analysisService';
import { DocumentService } from '../services/documentService';
import { TranslationService } from '../services/translationService';
import { sendSuccess, sendError } from '../utils/apiResponse';
import { logger } from '../utils/logger';

export class AnalysisController {
  public static async createAnalysis(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);

      let text = (req.body.text || req.body.description || '').trim();
      let documentMetadata: any = null;

      const documentLanguage = (req.body.documentLanguage || 'auto').toLowerCase();
      const translateForAnalysis =
        req.body.translateForAnalysis !== 'false' && req.body.translateForAnalysis !== false;

      if (req.file) {
        const docResult = await DocumentService.extractDocument(
          req.file.buffer,
          req.file.originalname,
          req.file.mimetype
        );

        if (docResult.overallStatus === 'SCANNED_UNPROCESSED' && docResult.text.trim().length < 20) {
          return sendError(
            res,
            'The uploaded document contains scanned pages or images, but the OCR engine is currently unavailable on the server. Please upload a text-searchable PDF, DOCX, or plain text file.',
            400
          );
        }

        const extractedTrimmed = docResult.text.trim();
        if (extractedTrimmed.length < 20 && text.length < 20) {
          return sendError(
            res,
            'The uploaded document yielded insufficient readable text (it may be a scanned/image-only PDF or blank file). Please upload a text-searchable PDF, DOCX, TXT, or paste the case narrative manually.',
            400
          );
        }

        documentMetadata = {
          filename: docResult.filename,
          documentType: docResult.documentType,
          pageCount: docResult.pageCount,
          extractionMethod: docResult.extractionMethod,
          overallStatus: docResult.overallStatus,
          warnings: docResult.warnings ? [...docResult.warnings] : [],
          pages: docResult.pages
        };

        // Multilingual Document Intelligence & Pre-Analysis Translation Gate
        const langInfo = TranslationService.detectLanguage(extractedTrimmed);
        const isHindi =
          documentLanguage === 'hi' ||
          langInfo.primaryLanguage === 'hi' ||
          (langInfo.devanagariRatio >= 0.25 && langInfo.devanagariCount >= 8);

        if (isHindi) {
          if (translateForAnalysis) {
            try {
              const transResult = await TranslationService.translateDocumentText(extractedTrimmed, {
                sourceLanguage: 'hi',
                targetLanguage: 'en',
                consentExternalService: false,
                preserveCitations: true
              });

              documentMetadata.originalExtractedText = extractedTrimmed;
              documentMetadata.preAnalysisTranslation = transResult;
              documentMetadata.translationForAnalysis = true;
              documentMetadata.detectedLanguage = langInfo.detectedLanguage;
              documentMetadata.primaryLanguage = langInfo.primaryLanguage;

              // Pass verified English translation to downstream legal research & ML models
              text = text ? `${text}\n\n${transResult.translatedText}` : transResult.translatedText;
            } catch (transErr: any) {
              logger.error(`Pre-analysis translation failed: ${transErr.message}`);
              documentMetadata.warnings.push(
                `Automatic Hindi-to-English translation encountered an error: ${transErr.message}. Original text retained.`
              );
              text = text ? `${text}\n\n${extractedTrimmed}` : extractedTrimmed;
            }
          } else {
            // translateForAnalysis is explicitly disabled by the user
            const descLang = TranslationService.detectLanguage(text);
            if (descLang.primaryLanguage === 'en' && text.length >= 20) {
              documentMetadata.originalExtractedText = extractedTrimmed;
              documentMetadata.translationForAnalysis = false;
              documentMetadata.detectedLanguage = langInfo.detectedLanguage;
              documentMetadata.primaryLanguage = langInfo.primaryLanguage;
              documentMetadata.warnings.push(
                'Document was identified as Hindi but "Translate for analysis" was disabled. Legal research and ML inference proceeded using the provided English narrative.'
              );
              // text remains English narrative without appending untranslated Hindi
            } else {
              return sendError(
                res,
                'Hindi document detected, but "Translate for analysis" was disabled. The legal research and prediction pipeline requires English text. Please enable translation in the intake form or provide an English factual summary.',
                400
              );
            }
          }
        } else {
          // English document (no unnecessary translation overhead)
          documentMetadata.translationForAnalysis = false;
          documentMetadata.detectedLanguage = langInfo.detectedLanguage;
          documentMetadata.primaryLanguage = langInfo.primaryLanguage;
          text = text ? `${text}\n\n${extractedTrimmed}` : extractedTrimmed;
        }
      } else if (text.trim().length >= 15) {
        // Direct factual narrative submission without file attachment
        const directLang = TranslationService.detectLanguage(text);
        const isDirectHindi =
          documentLanguage === 'hi' ||
          directLang.primaryLanguage === 'hi' ||
          (directLang.devanagariRatio >= 0.25 && directLang.devanagariCount >= 8);

        if (isDirectHindi) {
          if (translateForAnalysis) {
            try {
              const transResult = await TranslationService.translateDocumentText(text, {
                sourceLanguage: 'hi',
                targetLanguage: 'en',
                consentExternalService: false,
                preserveCitations: true
              });

              documentMetadata = {
                filename: 'Factual Statement Narrative',
                documentType: 'text',
                pageCount: 1,
                extractionMethod: 'native',
                overallStatus: 'SUCCESS',
                warnings: [],
                pages: [
                  {
                    pageNumber: 1,
                    text,
                    extractionMethod: 'native',
                    scriptType: 'printed',
                    confidence: 1.0,
                    uncertainTokens: [],
                    status: 'SUCCESS'
                  }
                ],
                originalExtractedText: text,
                preAnalysisTranslation: transResult,
                translationForAnalysis: true,
                detectedLanguage: directLang.detectedLanguage,
                primaryLanguage: directLang.primaryLanguage
              };
              text = transResult.translatedText;
            } catch (err: any) {
              logger.error(`Direct text pre-analysis translation error: ${err.message}`);
            }
          } else {
            return sendError(
              res,
              'Hindi narrative detected, but "Translate for analysis" was disabled. The legal research and prediction pipeline requires English text. Please enable translation or provide English submissions.',
              400
            );
          }
        }
      }

      if (!req.body.caseId && text.trim().length < 15) {
        return sendError(
          res,
          'Please provide a case description or upload a readable legal document (minimum 15 characters).',
          400
        );
      }

      const analysis = await AnalysisService.performAnalysis(req.user.id, {
        caseId: req.body.caseId,
        caseTitle: req.body.caseTitle || req.body.title,
        description: req.body.description,
        court: req.body.court,
        category: req.body.category,
        text,
        documentMetadata
      });

      return sendSuccess(res, analysis, 'Case analysis completed successfully.', 201);
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getAnalyses(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);

      const page = Math.max(1, parseInt((req.query.page as string) || '1', 10) || 1);
      const limit = Math.min(50, Math.max(1, parseInt((req.query.limit as string) || '10', 10) || 10));
      const search = req.query.search as string;
      const category = req.query.category as string;

      const result = await AnalysisService.getUserAnalyses(req.user.id, { page, limit, search, category });
      return sendSuccess(res, result.analyses, 'Analysis history retrieved successfully.', 200, {
        total: result.total,
        page: result.page,
        limit: result.limit,
        totalPages: result.totalPages,
        persistenceMode: result.persistenceMode
      });
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getAnalysisById(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const found = await AnalysisService.getAnalysisById(req.user.id, req.params.id);
      return sendSuccess(res, found, 'Analysis report retrieved successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 404);
    }
  }

  public static async updateAnalysis(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const updated = await AnalysisService.updateAnalysis(req.user.id, req.params.id, {
        researchNotes: req.body.researchNotes,
        editedDrafts: req.body.editedDrafts,
        caseTitle: req.body.caseTitle
      });
      return sendSuccess(res, updated, 'Research notes and drafts saved successfully.');
    } catch (err: any) {
      const status = err.message.includes('not found') ? 404 : 400;
      return sendError(res, err.message, status);
    }
  }

  public static async deleteAnalysis(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      await AnalysisService.deleteAnalysis(req.user.id, req.params.id);
      return sendSuccess(res, null, 'Analysis record deleted successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }
}
