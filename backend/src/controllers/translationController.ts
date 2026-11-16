import { Request, Response } from 'express';
import { TranslationService, TranslationOptions } from '../services/translationService';
import { sendSuccess, sendError } from '../utils/apiResponse';
import { logger } from '../utils/logger';

export class TranslationController {
  /**
   * POST /api/v1/translation/detect-language
   * Analyzes text and returns script statistics and detected language.
   */
  public static async detectLanguage(req: Request, res: Response) {
    try {
      const { text } = req.body;
      if (!text || typeof text !== 'string') {
        return sendError(res, 'Field "text" (string) is required for language detection.', 400);
      }

      const detection = TranslationService.detectLanguage(text);
      return sendSuccess(res, detection, 'Language detected successfully.');
    } catch (err: any) {
      logger.error(`Language detection error: ${err.message}`);
      return sendError(res, err.message || 'Failed to detect document language.', 500);
    }
  }

  /**
   * POST /api/v1/translation/translate
   * Translates legal document text between English and Hindi.
   */
  public static async translate(req: Request, res: Response) {
    try {
      const { text, sourceLanguage, targetLanguage, consentExternalService, preserveCitations } = req.body;

      if (!text || typeof text !== 'string' || !text.trim()) {
        return sendError(res, 'Field "text" (non-empty string) is required for translation.', 400);
      }

      if (targetLanguage && targetLanguage !== 'en' && targetLanguage !== 'hi') {
        return sendError(res, `Target language '${targetLanguage}' is not supported. Supported: 'en', 'hi'.`, 400);
      }

      if (sourceLanguage && sourceLanguage !== 'auto' && sourceLanguage !== 'en' && sourceLanguage !== 'hi') {
        return sendError(res, `Source language '${sourceLanguage}' is not supported. Supported: 'auto', 'en', 'hi'.`, 400);
      }

      const options: TranslationOptions = {
        sourceLanguage: sourceLanguage || 'auto',
        targetLanguage: (targetLanguage as 'en' | 'hi') || 'hi',
        consentExternalService: Boolean(consentExternalService),
        preserveCitations: preserveCitations !== false
      };

      const result = await TranslationService.translateDocumentText(text, options);
      return sendSuccess(res, result, 'Document translated successfully.');
    } catch (err: any) {
      logger.error(`Document translation error: ${err.message}`);
      return sendError(res, err.message || 'Failed to translate legal document.', 500);
    }
  }
}
