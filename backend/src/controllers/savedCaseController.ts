import { Response } from 'express';
import mongoose from 'mongoose';
import { AuthRequest } from '../middleware/auth';
import { SavedCase } from '../models/SavedCase';
import { getDBStatus } from '../config/db';
import { judgmentRegistry } from '../utils/judgmentRegistry';
import { sendSuccess, sendError } from '../utils/apiResponse';

const memorySaved: Map<string, any> = new Map();

export class SavedCaseController {
  public static async saveCase(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);

      const {
        precedentId,
        precedentCode,
        analysisId,
        caseTitle,
        court,
        citation,
        officialSourceUrl,
        officialSourceVerified,
        secondaryReferenceUrl,
        sourceUrl,
        verificationStatus,
        category,
        notes
      } = req.body;

      // Resolve verified registry metadata whenever precedent matches known corpus ID or title
      const reg =
        (precedentCode && judgmentRegistry.findById(precedentCode)) ||
        (precedentId && judgmentRegistry.findById(precedentId)) ||
        (caseTitle && judgmentRegistry.findByKeyword(caseTitle)) ||
        undefined;

      const resolvedCode = precedentCode || (precedentId && !mongoose.Types.ObjectId.isValid(precedentId) ? precedentId : reg?.id || '');
      const resolvedObjectPrecedentId =
        precedentId && mongoose.Types.ObjectId.isValid(precedentId)
          ? new mongoose.Types.ObjectId(precedentId)
          : undefined;
      const resolvedObjectAnalysisId =
        analysisId && mongoose.Types.ObjectId.isValid(analysisId)
          ? new mongoose.Types.ObjectId(analysisId)
          : undefined;

      const finalTitle = reg?.caseTitle || caseTitle || 'Saved Judgment';
      const finalCourt = reg?.court || court || 'Supreme Court of India';
      const finalCitation = reg?.citation || citation || '';
      const finalOfficialUrl = reg?.officialSourceUrl ?? officialSourceUrl ?? '';
      const finalOfficialVerified = reg ? Boolean(reg.officialSourceVerified) : Boolean(officialSourceVerified);
      const finalSecondaryUrl = reg?.secondaryReferenceUrl ?? secondaryReferenceUrl ?? '';
      const finalSourceUrl = reg?.sourceUrl || sourceUrl || finalOfficialUrl || finalSecondaryUrl || '';
      const finalVerificationStatus = reg?.verificationStatus || verificationStatus || (finalOfficialVerified ? 'verified_official' : 'unverified');
      const finalCategory = reg?.category || category || 'General';

      const dbStatus = getDBStatus();

      if (dbStatus.isConnected) {
        const userObjectId = mongoose.Types.ObjectId.isValid(req.user.id)
          ? new mongoose.Types.ObjectId(req.user.id)
          : req.user.id;

        // Avoid duplicate bookmarks for the same precedent/title by this user
        const existingQuery: any = { userId: userObjectId };
        if (resolvedCode) {
          existingQuery.precedentCode = resolvedCode;
        } else {
          existingQuery.caseTitle = finalTitle;
        }

        const existing = await SavedCase.findOne(existingQuery);
        if (existing) {
          if (typeof notes === 'string' && notes.trim()) {
            existing.notes = notes.trim();
            await existing.save();
          }
          return sendSuccess(res, existing, 'Judgment is already bookmarked.', 200);
        }

        const item = await SavedCase.create({
          userId: userObjectId,
          precedentId: resolvedObjectPrecedentId,
          precedentCode: resolvedCode,
          analysisId: resolvedObjectAnalysisId,
          caseTitle: finalTitle,
          court: finalCourt,
          citation: finalCitation,
          officialSourceUrl: finalOfficialUrl,
          officialSourceVerified: finalOfficialVerified,
          secondaryReferenceUrl: finalSecondaryUrl,
          sourceUrl: finalSourceUrl,
          verificationStatus: finalVerificationStatus,
          category: finalCategory,
          notes: notes || ''
        });
        return sendSuccess(res, item, 'Judgment saved to bookmarks.', 201);
      } else {
        const existing = Array.from(memorySaved.values()).find(
          s =>
            s.userId === req.user!.id &&
            ((resolvedCode && s.precedentCode === resolvedCode) || s.caseTitle === finalTitle)
        );
        if (existing) {
          if (typeof notes === 'string' && notes.trim()) {
            existing.notes = notes.trim();
            existing.updatedAt = new Date();
          }
          return sendSuccess(res, existing, 'Judgment is already bookmarked.', 200);
        }

        const id = 'saved_' + Date.now();
        const item = {
          _id: id,
          id,
          userId: req.user.id,
          precedentId: resolvedObjectPrecedentId ? String(resolvedObjectPrecedentId) : undefined,
          precedentCode: resolvedCode,
          analysisId,
          caseTitle: finalTitle,
          court: finalCourt,
          citation: finalCitation,
          officialSourceUrl: finalOfficialUrl,
          officialSourceVerified: finalOfficialVerified,
          secondaryReferenceUrl: finalSecondaryUrl,
          sourceUrl: finalSourceUrl,
          verificationStatus: finalVerificationStatus,
          category: finalCategory,
          notes: notes || '',
          createdAt: new Date(),
          updatedAt: new Date()
        };
        memorySaved.set(id, item);
        return sendSuccess(res, item, 'Judgment saved to bookmarks.', 201);
      }
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async getSavedCases(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const userId = req.user.id;
      const dbStatus = getDBStatus();

      if (dbStatus.isConnected) {
        const userObjectId = mongoose.Types.ObjectId.isValid(userId)
          ? new mongoose.Types.ObjectId(userId)
          : userId;
        const items = await SavedCase.find({ userId: userObjectId }).sort({ createdAt: -1 });
        return sendSuccess(res, items, 'Saved judgments retrieved.');
      } else {
        const items = Array.from(memorySaved.values())
          .filter(s => s.userId === userId)
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        return sendSuccess(res, items, 'Saved judgments retrieved.');
      }
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async updateSavedCase(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const { id } = req.params;
      const notes = typeof req.body.notes === 'string' ? req.body.notes : '';
      const dbStatus = getDBStatus();

      if (dbStatus.isConnected) {
        if (!mongoose.Types.ObjectId.isValid(id)) {
          return sendError(res, 'Bookmark not found.', 404);
        }
        const userObjectId = mongoose.Types.ObjectId.isValid(req.user.id)
          ? new mongoose.Types.ObjectId(req.user.id)
          : req.user.id;
        const updated = await SavedCase.findOneAndUpdate(
          { _id: new mongoose.Types.ObjectId(id), userId: userObjectId },
          { notes },
          { new: true }
        );
        if (!updated) return sendError(res, 'Bookmark not found.', 404);
        return sendSuccess(res, updated, 'Bookmark notes updated.');
      } else {
        const item = memorySaved.get(id);
        if (!item || item.userId !== req.user.id) {
          return sendError(res, 'Bookmark not found.', 404);
        }
        item.notes = notes;
        item.updatedAt = new Date();
        memorySaved.set(id, item);
        return sendSuccess(res, item, 'Bookmark notes updated.');
      }
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }

  public static async deleteSavedCase(req: AuthRequest, res: Response) {
    try {
      if (!req.user) return sendError(res, 'Unauthorized', 401);
      const userId = req.user.id;
      const { id } = req.params;
      const dbStatus = getDBStatus();

      if (dbStatus.isConnected) {
        if (!mongoose.Types.ObjectId.isValid(id)) {
          return sendError(res, 'Bookmark not found.', 404);
        }
        const userObjectId = mongoose.Types.ObjectId.isValid(userId)
          ? new mongoose.Types.ObjectId(userId)
          : userId;
        const deleted = await SavedCase.findOneAndDelete({
          _id: new mongoose.Types.ObjectId(id),
          userId: userObjectId
        });
        if (!deleted) return sendError(res, 'Bookmark not found.', 404);
        return sendSuccess(res, null, 'Bookmark removed.');
      } else {
        const item = memorySaved.get(id);
        if (!item || item.userId !== userId) {
          return sendError(res, 'Bookmark not found.', 404);
        }
        memorySaved.delete(id);
        return sendSuccess(res, null, 'Bookmark removed.');
      }
    } catch (err: any) {
      return sendError(res, err.message, 400);
    }
  }
}
