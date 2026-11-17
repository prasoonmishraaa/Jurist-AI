import mongoose from 'mongoose';
import { Case, ICase } from '../models/Case';
import { getDBStatus } from '../config/db';

const memoryCases: Map<string, any> = new Map();

export class CaseService {
  public static async createCase(
    userId: string,
    data: {
      title: string;
      description: string;
      court?: string;
      category?: string;
      uploadedDocuments?: any[];
    }
  ) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const newCase = await Case.create({
        userId: new mongoose.Types.ObjectId(userId),
        title: data.title,
        description: data.description,
        court: data.court || 'Supreme Court of India',
        category: data.category || 'General',
        uploadedDocuments: data.uploadedDocuments || [],
        status: 'draft'
      });
      return newCase;
    } else {
      const caseId = 'case_' + Date.now();
      const mockCase = {
        _id: caseId,
        id: caseId,
        userId,
        title: data.title,
        description: data.description,
        court: data.court || 'Supreme Court of India',
        category: data.category || 'General',
        uploadedDocuments: data.uploadedDocuments || [],
        status: 'draft',
        createdAt: new Date(),
        updatedAt: new Date()
      };
      memoryCases.set(caseId, mockCase);
      return mockCase;
    }
  }

  public static async getUserCases(
    userId: string,
    options: { page?: number; limit?: number; search?: string; category?: string } = {}
  ) {
    const { page = 1, limit = 10, search, category } = options;
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const query: any = { userId: new mongoose.Types.ObjectId(userId) };

      if (category && category !== 'All') {
        query.category = category;
      }

      if (search) {
        query.$or = [
          { title: { $regex: search, $options: 'i' } },
          { description: { $regex: search, $options: 'i' } }
        ];
      }

      const total = await Case.countDocuments(query);
      const cases = await Case.find(query)
        .sort({ createdAt: -1 })
        .skip((page - 1) * limit)
        .limit(limit);

      return {
        cases,
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit)
      };
    } else {
      let filtered = Array.from(memoryCases.values()).filter(c => c.userId === userId);

      if (category && category !== 'All') {
        filtered = filtered.filter(c => c.category === category);
      }

      if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(c => c.title.toLowerCase().includes(s) || c.description.toLowerCase().includes(s));
      }

      filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      const total = filtered.length;
      const paginated = filtered.slice((page - 1) * limit, page * limit);

      return {
        cases: paginated,
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit)
      };
    }
  }

  public static async getCaseById(userId: string, caseId: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const found = await Case.findOne({
        _id: new mongoose.Types.ObjectId(caseId),
        userId: new mongoose.Types.ObjectId(userId)
      });
      if (!found) throw new Error('Case not found or access denied.');
      return found;
    } else {
      const found = memoryCases.get(caseId);
      if (!found || found.userId !== userId) {
        throw new Error('Case not found or access denied.');
      }
      return found;
    }
  }

  public static async deleteCase(userId: string, caseId: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const res = await Case.findOneAndDelete({
        _id: new mongoose.Types.ObjectId(caseId),
        userId: new mongoose.Types.ObjectId(userId)
      });
      if (!res) throw new Error('Case not found or access denied.');
      return true;
    } else {
      const found = memoryCases.get(caseId);
      if (!found || found.userId !== userId) {
        throw new Error('Case not found or access denied.');
      }
      memoryCases.delete(caseId);
      return true;
    }
  }
}
