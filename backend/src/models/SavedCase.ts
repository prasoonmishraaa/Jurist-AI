import mongoose, { Document, Schema } from 'mongoose';

export interface ISavedCase extends Document {
  userId: mongoose.Types.ObjectId;
  precedentId?: mongoose.Types.ObjectId;
  precedentCode?: string;
  analysisId?: mongoose.Types.ObjectId;
  caseTitle: string;
  court: string;
  citation: string;
  officialSourceUrl?: string;
  officialSourceVerified: boolean;
  secondaryReferenceUrl?: string;
  sourceUrl: string;
  verificationStatus?: string;
  category: string;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

const SavedCaseSchema = new Schema<ISavedCase>(
  {
    userId: {
      type: Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true
    },
    precedentId: {
      type: Schema.Types.ObjectId,
      ref: 'Precedent'
    },
    precedentCode: {
      type: String,
      default: ''
    },
    analysisId: {
      type: Schema.Types.ObjectId,
      ref: 'Analysis'
    },
    caseTitle: {
      type: String,
      required: true
    },
    court: {
      type: String,
      required: true
    },
    citation: {
      type: String,
      default: ''
    },
    officialSourceUrl: {
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
    sourceUrl: {
      type: String,
      default: ''
    },
    verificationStatus: {
      type: String,
      default: 'unverified'
    },
    category: {
      type: String,
      default: 'General'
    },
    notes: {
      type: String,
      default: ''
    }
  },
  {
    timestamps: true
  }
);

SavedCaseSchema.index({ userId: 1, precedentCode: 1 });

export const SavedCase = mongoose.models.SavedCase || mongoose.model<ISavedCase>('SavedCase', SavedCaseSchema);
