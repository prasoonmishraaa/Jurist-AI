import mongoose from 'mongoose';
import { Precedent } from '../models/Precedent';
import { getDBStatus } from '../config/db';
import { judgmentRegistry } from '../utils/judgmentRegistry';

export class PrecedentService {
  public static async listPrecedents(options: {
    page?: number;
    limit?: number;
    search?: string;
    category?: string;
    court?: string;
  }) {
    const { page = 1, limit = 10, search, category, court } = options;
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const query: any = {};

      if (category && category !== 'All') {
        query.category = category;
      }

      if (court && court !== 'All') {
        query.court = court;
      }

      if (search) {
        query.$or = [
          { caseTitle: { $regex: search, $options: 'i' } },
          { citation: { $regex: search, $options: 'i' } },
          { summary: { $regex: search, $options: 'i' } },
          { legalProvisions: { $regex: search, $options: 'i' } }
        ];
      }

      const total = await Precedent.countDocuments(query);
      if (total > 0) {
        const precedents = await Precedent.find(query)
          .sort({ judgmentDate: -1 })
          .skip((page - 1) * limit)
          .limit(limit);

        return {
          precedents,
          total,
          page,
          limit,
          totalPages: Math.ceil(total / limit)
        };
      }
      // If DB is connected but collection is not seeded yet, gracefully serve verified registry corpus
    }

    let items = [...judgmentRegistry.getAll()];

    if (category && category !== 'All') {
      items = items.filter(c => c.category === category);
    }

    if (court && court !== 'All') {
      items = items.filter(c => c.court === court);
    }

    if (search) {
      const s = search.toLowerCase();
      items = items.filter(
        c =>
          (c.caseTitle && c.caseTitle.toLowerCase().includes(s)) ||
          (c.citation && c.citation.toLowerCase().includes(s)) ||
          (c.summary && c.summary.toLowerCase().includes(s)) ||
          (Array.isArray(c.legalProvisions) && c.legalProvisions.some(p => p.toLowerCase().includes(s)))
      );
    }

    items.sort((a, b) => (b.judgmentDate || '').localeCompare(a.judgmentDate || ''));

    const total = items.length;
    const paginated = items.slice((page - 1) * limit, page * limit);

    return {
      precedents: paginated,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit)
    };
  }

  public static async getPrecedentById(id: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      if (mongoose.Types.ObjectId.isValid(id)) {
        const found = await Precedent.findById(id);
        if (found) return found;
      }
      const foundByCustomId = await Precedent.findOne({
        $or: [{ caseIdentifier: id }, { citation: id }]
      });
      if (foundByCustomId) return foundByCustomId;
    }

    const match = judgmentRegistry.findById(id) || judgmentRegistry.findByKeyword(id);
    if (match) return match;

    throw new Error('Precedent not found.');
  }
}
