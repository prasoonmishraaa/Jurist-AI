import mongoose, { Document, Schema } from 'mongoose';

export interface IPrecedent extends Document {
  precedentCode?: string;
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
  officialSourceUrl?: string;
  officialSourceLabel?: string;
  officialSourceVerified: boolean;
  secondaryReferenceUrl?: string;
  secondaryReferenceLabel?: string;
  sourceUrl: string;
  verificationStatus: string;
  verificationNote?: string;
  article141Status?: string;
  obiterAndScopeNote?: string;
  subsequentTreatment?: string;
  outcome?: string;
  outcomeRationale?: string;
  createdAt: Date;
  updatedAt: Date;
}

const PrecedentSchema = new Schema<IPrecedent>(
  {
    precedentCode: {
      type: String,
      index: true
    },
    caseTitle: {
      type: String,
      required: true,
      trim: true,
      index: true
    },
    court: {
      type: String,
      required: true,
      index: true
    },
    judgmentDate: {
      type: String,
      required: true,
      index: true
    },
    caseIdentifier: {
      type: String,
      required: true
    },
    citation: {
      type: String,
      required: true,
      index: true
    },
    bench: {
      type: String
    },
    category: {
      type: String,
      required: true,
      index: true
    },
    legalProvisions: [{
      type: String
    }],
    summary: {
      type: String,
      required: true
    },
    judgmentText: {
      type: String,
      required: true
    },
    officialSourceUrl: {
      type: String,
      default: ''
    },
    officialSourceLabel: {
      type: String,
      default: ''
    },
    officialSourceVerified: {
      type: Boolean,
      default: false
    },
    secondaryReferenceUrl: {
      type: String,
      default: ''
    },
    secondaryReferenceLabel: {
      type: String,
      default: ''
    },
    sourceUrl: {
      type: String,
      default: ''
    },
    verificationStatus: {
      type: String,
      default: 'secondary_verified_official_unverified',
      index: true
    },
    verificationNote: {
      type: String,
      default: ''
    },
    article141Status: {
      type: String,
      default: ''
    },
    obiterAndScopeNote: {
      type: String,
      default: ''
    },
    subsequentTreatment: {
      type: String,
      default: ''
    },
    outcome: {
      type: String,
      enum: ['Allowed', 'Dismissed', 'Partially Allowed', 'Remanded', 'Disposed']
    },
    outcomeRationale: {
      type: String
    }
  },
  {
    timestamps: true
  }
);

PrecedentSchema.index({ caseTitle: 'text', judgmentText: 'text', summary: 'text' });

export const Precedent = mongoose.models.Precedent || mongoose.model<IPrecedent>('Precedent', PrecedentSchema);
