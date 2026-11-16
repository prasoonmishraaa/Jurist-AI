import { Response } from 'express';
import { AuthRequest } from '../middleware/auth';
import { CaseService } from '../services/caseService';
import { DocumentService } from '../services/documentService';
import { sendSuccess, sendError } from '../utils/apiResponse';

export class CaseController {
  public static async createCase(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);

      const { title, description, court, category } = req.body;
      const uploadedDocs: any[] = [];

      // If document was uploaded
      if (req.file) {
        const docResult = await DocumentService.extractDocument(
          req.file.buffer,
          req.file.originalname,
          req.file.mimetype
        );

        uploadedDocs.push({
          originalName: req.file.originalname,
          fileName: `doc_${Date.now()}_${req.file.originalname}`,
          filePath: 'memory-buffer',
          fileSize: req.file.size,
          mimeType: req.file.mimetype,
          extractedText: docResult.text,
          extractedTextSnippet: docResult.text.slice(0, 10000), // preserve substantial preview snippet
          documentMetadata: {
            pageCount: docResult.pageCount,
            extractionMethod: docResult.extractionMethod,
            overallStatus: docResult.overallStatus,
            warnings: docResult.warnings,
            pages: docResult.pages
          },
          uploadedAt: new Date()
        });
      }

      const newCase = await CaseService.createCase(req.user.id, {
        title,
        description,
        court,
        category,
        uploadedDocuments: uploadedDocs
      });

      return sendSuccess(res, newCase, 'Case created successfully.', 201);
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getCases(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);

      const page = parseInt(req.query.page as string || '1', 10);
      const limit = parseInt(req.query.limit as string || '10', 10);
      const search = req.query.search as string;
      const category = req.query.category as string;

      const result = await CaseService.getUserCases(req.user.id, { page, limit, search, category });
      return sendSuccess(res, result.cases, 'Cases retrieved successfully.', 200, {
        total: result.total,
        page: result.page,
        limit: result.limit,
        totalPages: result.totalPages
      });
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getCaseById(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const found = await CaseService.getCaseById(req.user.id, req.params.id);
      return sendSuccess(res, found, 'Case retrieved successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 404);
    }
  }

  public static async deleteCase(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      await CaseService.deleteCase(req.user.id, req.params.id);
      return sendSuccess(res, null, 'Case deleted successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }
}
