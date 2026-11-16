import path from 'path';
import fs from 'fs';

export interface VerifiedJudgmentRecord {
  id: string;
  caseTitle: string;
  court: string;
  judgmentDate: string;
  caseIdentifier: string;
  citation: string;
  bench?: string;
  category: string;
  legalProvisions: string[];
  summary: string;
  judgmentText: string;
  officialSourceUrl: string;
  officialSourceLabel: string;
  officialSourceVerified: boolean;
  secondaryReferenceUrl: string;
  secondaryReferenceLabel: string;
  sourceUrl: string;
  verificationStatus: 'verified_official' | 'secondary_verified_official_unverified' | 'unverified';
  verificationNote?: string;
  article141Status?: string;
  obiterAndScopeNote?: string;
  subsequentTreatment?: string;
  outcome?: string;
  outcomeRationale?: string;
}

class JudgmentSourceRegistry {
  private records: VerifiedJudgmentRecord[] = [];

  constructor() {
    this.load();
  }

  private load() {
    const candidatePaths = [
      path.resolve(__dirname, '../integrations/artifacts/precedents_artifacts.json'),
      path.resolve(__dirname, '../../src/integrations/artifacts/precedents_artifacts.json'),
      path.resolve(__dirname, '../../../ml-service/app/datasets/indian_judgments.json')
    ];

    for (const p of candidatePaths) {
      if (fs.existsSync(p)) {
        try {
          const raw = JSON.parse(fs.readFileSync(p, 'utf-8'));
          this.records = Array.isArray(raw) ? raw : raw.corpus || [];
          if (this.records.length > 0) break;
        } catch {
          // continue checking candidates
        }
      }
    }
  }

  public getAll(): VerifiedJudgmentRecord[] {
    if (this.records.length === 0) this.load();
    return this.records;
  }

  public findById(id: string): VerifiedJudgmentRecord | undefined {
    return this.getAll().find(r => r.id === id || r.caseIdentifier === id || r.citation === id);
  }

  public findByKeyword(keyword: string): VerifiedJudgmentRecord | undefined {
    const kw = keyword.toLowerCase();
    return this.getAll().find(
      r =>
        r.caseTitle.toLowerCase().includes(kw) ||
        r.citation.toLowerCase().includes(kw) ||
        r.id.toLowerCase() === kw
    );
  }
}

export const judgmentRegistry = new JudgmentSourceRegistry();
