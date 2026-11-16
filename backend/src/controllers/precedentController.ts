import { Request, Response } from 'express';
import { PrecedentService } from '../services/precedentService';
import { getCorpusStatistics } from '../utils/corpusStats';
import { sendSuccess, sendError } from '../utils/apiResponse';

export class PrecedentController {
  public static async getCorpusStats(_req: Request, res: Response) {
    try {
      const stats = await getCorpusStatistics();
      return sendSuccess(res, stats, 'Corpus statistics retrieved successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 500);
    }
  }

  public static async getPrecedents(req: Request, res: Response) {
    try {
      const page = parseInt(req.query.page as string || '1', 10);
      const limit = parseInt(req.query.limit as string || '10', 10);
      const search = req.query.search as string;
      const category = req.query.category as string;
      const court = req.query.court as string;

      const result = await PrecedentService.listPrecedents({ page, limit, search, category, court });
      return sendSuccess(res, result.precedents, 'Precedents retrieved successfully.', 200, {
        total: result.total,
        page: result.page,
        limit: result.limit,
        totalPages: result.totalPages
      });
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getPrecedentById(req: Request, res: Response) {
    try {
      const precedent = await PrecedentService.getPrecedentById(req.params.id);
      return sendSuccess(res, precedent, 'Precedent details retrieved successfully.');
    } catch (err: any) {
      return sendError(res, err.message, 404);
    }
  }
}
