import mongoose, { Document, Schema } from 'mongoose';

export interface ICaseDocument {
  originalName: string;
  fileName: string;
  filePath: string;
  fileSize: number;
  mimeType: string;
  extractedText?: string;
  extractedTextSnippet?: string;
  documentMetadata?: any;
  uploadedAt: Date;
}

export interface ICase extends Document {
  userId: mongoose.Types.ObjectId;
  title: string;
  description: string;
  court: string;
  category: string;
  uploadedDocuments: ICaseDocument[];
  status: 'draft' | 'analyzed' | 'archived';
  createdAt: Date;
  updatedAt: Date;
}

const CaseDocumentSchema = new Schema<ICaseDocument>({
  originalName: { type: String, required: true },
  fileName: { type: String, required: true },
  filePath: { type: String, required: true },
  fileSize: { type: Number, required: true },
  mimeType: { type: String, required: true },
  extractedText: { type: String },
  extractedTextSnippet: { type: String },
  documentMetadata: { type: Schema.Types.Mixed },
  uploadedAt: { type: Date, default: Date.now }
});

const CaseSchema = new Schema<ICase>(
  {
    userId: {
      type: Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true
    },
    title: {
      type: String,
      required: [true, 'Case title is required'],
      trim: true,
      maxlength: [200, 'Title cannot exceed 200 characters']
    },
    description: {
      type: String,
      required: [true, 'Case description is required'],
      trim: true
    },
    court: {
      type: String,
      required: true,
      trim: true,
      default: 'Supreme Court of India'
    },
    category: {
      type: String,
      required: true,
      trim: true,
      default: 'General'
    },
    uploadedDocuments: [CaseDocumentSchema],
    status: {
      type: String,
      enum: ['draft', 'analyzed', 'archived'],
      default: 'draft',
      index: true
    }
  },
  {
    timestamps: true
  }
);

CaseSchema.index({ userId: 1, createdAt: -1 });

export const Case = mongoose.models.Case || mongoose.model<ICase>('Case', CaseSchema);
