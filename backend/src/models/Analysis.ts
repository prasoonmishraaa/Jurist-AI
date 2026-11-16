import mongoose, { Document, Schema } from 'mongoose';
import { ApplicableLawAssessment } from '../services/legislationService';

export type PrecedentRelevanceClass =
  | 'Directly relevant'
  | 'Supporting authority'
  | 'Constitutional background'
  | 'Distinguishing authority'
  | 'Potentially adverse authority'
  | 'Further research required';

export interface IMatchedPrecedent {
  id?: string;
  precedentId?: mongoose.Types.ObjectId;
  caseTitle: string;
  court: string;
  judgmentDate: string;
  citation: string;
  bench?: string;
  category: string;
  legalProvisions: string[];
  summary: string;
  judgmentText?: string;
  officialSourceUrl?: string;
  officialSourceLabel?: string;
  officialSourceVerified: boolean;
  secondaryReferenceUrl?: string;
  secondaryReferenceLabel?: string;
  sourceUrl: string;
  verificationStatus: string;
  verificationNote?: string;
  similarityScore?: number;
  matchedTerms: string[];
  relevanceClassification: PrecedentRelevanceClass;
  retrievalReason: string;
  article141Status?: string;
  obiterAndScopeNote?: string;
  subsequentTreatment?: string;
  historicalOutcome?: string;
  retrievalSignals?: IRetrievalSignalBreakdown;
}

export interface ISupportingPrecedent {
  id?: string;
  caseTitle: string;
  citation: string;
  court: string;
  bench?: string;
  judgmentDate?: string;
  ratioPrinciple: string;
  obiterNote?: string;
  applicationToFacts: string;
  officialSourceUrl?: string;
  officialSourceLabel?: string;
  officialSourceVerified: boolean;
  secondaryReferenceUrl?: string;
  secondaryReferenceLabel?: string;
  sourceUrl: string;
  verificationStatus?: string;
  authorityType: string;
}

/**
 * Breakdown of multi-modal retrieval signals for a precedent.
 */
export interface IRetrievalSignalBreakdown {
  tfidfRank?: number;
  bm25Rank?: number;
  semanticRank?: number;
  rrfScore?: number;
  activeModalities?: string[];
  matchedKeywords?: string[];
  relevanceExplanation?: string;
}

/**
 * Verifiable reference to a source document page/snippet.
 */
export interface ISourceDocumentPassage {
  documentName?: string;
  pageNumber?: number;
  totalDocumentPages?: number;
  textSnippet: string;
  extractionMethod: 'native' | 'ocr' | 'unresolved';
  pageConfidence?: number | null; // e.g. 0.8113 or 1.0 for native digital
  uncertainTokens: string[];
  hasLowConfidenceTokens: boolean;
  attributionStatus: 'verified' | 'unresolved' | 'unavailable';
}

/**
 * Verifiable pinpoint judgment passage or editorial paraphrase.
 */
export interface ISupportingJudgmentPassage {
  paragraphNumber?: number;
  verbatimQuote?: string;
  editorialParaphrase: string;
  officialSourcePage?: number;
  isDirectQuote: boolean;
  pinpointCitation?: string; // e.g. "Para 14, 2025 INSC 162"
  verificationSource?: string;
  verificationStatus?: 'character_verified' | 'editorial_paraphrase' | 'unverified';
}

/**
 * Epistemic confidence and OCR uncertainty gate assessment.
 */
export interface ITraceConfidenceAssessment {
  overallTraceReliability: 'high_confidence' | 'moderate_confidence' | 'requires_verification';
  ocrReliabilityCaveat?: string;
  isOcrUncertain: boolean;
}

/**
 * End-to-end evidence trace node linking source text to court submissions.
 */
export interface IEvidenceTraceNode {
  traceId: string;
  argumentId: string;
  groundNumber: string;
  
  // 1. Source Document Origin
  sourcePassage: ISourceDocumentPassage;
  
  // 2. Factual Classification
  factAssertion: {
    statement: string;
    classification: 'User-provided fact' | 'Party allegation' | 'Material fact' | 'Unresolved';
    factId?: string;
    isContested?: boolean;
  };
  
  // 3. Legal Issue & Statutory Regime
  legalIssueId?: string;
  legalIssueTitle?: string;
  statutoryProvision: string;
  statutoryRegime: string;
  
  // 4. Precedent Authority & Retrieval Breakdown
  precedent?: {
    id?: string;
    caseTitle: string;
    citation: string;
    court?: string;
    relevanceClassification?: PrecedentRelevanceClass | string;
    signals?: IRetrievalSignalBreakdown;
    officialSourceVerified: boolean;
    officialSourceUrl?: string;
  };
  
  // 5. Supporting Judgment Pinpoint Citation
  judgmentPassage?: ISupportingJudgmentPassage;
  
  // 6. Related Draft Legal Argument
  draftSubmissionSnippet?: string;
  
  // 7. Epistemic Confidence & OCR Guard
  confidenceAssessment: ITraceConfidenceAssessment;
  
  // 8. Explicit missing / unresolved relationships
  unresolvedRelationships?: string[];
}

export interface ICounterArgument {
  opposingGround: string;
  opposingLegalBasis: string;
  factualBasis: string;
  vulnerabilityAssessment: string;
  rebuttalStrategy: string;
  requiredEvidence: string;
}

export interface ILegalArgument {
  id: string;
  groundNumber: string;
  heading: string;
  legalQuestion: string;
  legalProposition: string;
  relevantFacts: string;
  applicableProvisions: string[];
  supportingPrecedents: ISupportingPrecedent[];
  ratioDecidendi: string;
  judicialReasoning: string;
  applicationToFacts: string;
  factualDistinctions: string;
  suggestedSubmission: string;
  draftDisclaimer: string;
  evidenceRequired: string[];
  weaknesses: string;
  limitations: string;
  counterarguments: ICounterArgument[];
  sourceTraceId?: string;
  ocrConfidenceWarning?: string;
}

export interface IAttributedFact {
  id: string; // e.g. "fact-1", "allegation-1"
  statement: string;
  classification: 'User-provided fact' | 'Party allegation' | 'Material fact' | 'Unresolved';
  pageNumber?: number;
  extractionMethod?: 'native' | 'ocr' | 'unresolved';
  pageConfidence?: number | null;
  uncertainTokens?: string[];
  attributionStatus: 'verified' | 'unresolved' | 'unavailable';
  sourceSnippet?: string;
}

export interface IChronologyEvent {
  date: string;
  event: string;
  involvedParties: string;
  sourceExcerpt: string;
  verificationStatus: 'User-provided fact' | 'Party allegation' | 'Unverified timeline';
  pageNumber?: number;
  extractionMethod?: 'native' | 'ocr' | 'unresolved';
  pageConfidence?: number | null;
  attributionStatus?: 'verified' | 'unresolved' | 'unavailable';
}

export interface IEvidenceAuditItem {
  documentName: string;
  purpose: string;
  status: 'Document to obtain / verify';
  relevanceNote: string;
}

export interface IAvailableRemedyOption {
  remedy: string;
  statutoryBasis: string;
  whenApplicable: string;
  cautionNote: string;
}

export interface ICaseUnderstanding {
  parties: { petitioners: string[]; respondents: string[] };
  materialFacts: string[];
  chronology: IChronologyEvent[];
  attributedFacts?: IAttributedFact[];
  factClassification: {
    userProvidedFacts: string[];
    partyAllegations: string[];
    reasonableInferences: string[];
    missingInformation: string[];
    factsRequiringVerification: string[];
  };
  disputedActions: string[];
  allegedViolations: string[];
  missingInformation: string[];
  evidenceAudit: IEvidenceAuditItem[];
  proceduralPosture: {
    detectedPosture: string;
    custodyStatus: 'in_custody_arrested' | 'apprehending_arrest' | 'released_on_bail' | 'civil_or_non_custodial' | 'unclear';
    availableRemedies: IAvailableRemedyOption[];
    remedyNote: string;
  };
  proceduralQuestions: string[];
}

export interface IJudicialTreatmentAssessment {
  assessmentTitle: string;
  researchScopeNote: string;
  historicalLegalPrinciples: string[];
  supportingAuthorities: Array<{
    caseTitle: string;
    citation: string;
    proposition: string;
  }>;
  distinguishingOrAdverseAuthorities: Array<{
    caseTitle: string;
    citation: string;
    distinctionNote: string;
  }>;
  keyFactualDeterminants: string[];
  researchLimitations: string[];
}

export interface IAnalysis extends Document {
  userId: mongoose.Types.ObjectId;
  caseId?: mongoose.Types.ObjectId;
  caseTitle: string;
  court: string;
  category: string;
  inputTextSnippet: string;
  fullText?: string;
  caseUnderstanding: ICaseUnderstanding;
  applicableLaw: ApplicableLawAssessment;
  extractedEntities: {
    parties?: { petitioners: string[]; respondents: string[] };
    courts?: string[];
    judges?: string[];
    statutes?: string[];
    sections?: string[];
    citations?: string[];
    legalTerms?: Array<{ term: string; definition: string }>;
    disclaimer?: string;
  };
  legalIssues: Array<{
    issue: string;
    relevantFacts?: string;
    statutoryProvision: string;
    supportingAuthorities?: string[];
    whyIssueMatters?: string;
    informationStillRequired?: string;
    description: string;
    matchedKeywords?: string[];
  }>;
  similarCases: IMatchedPrecedent[];
  legalArguments: ILegalArgument[];
  judicialTreatment: IJudicialTreatmentAssessment;
  evidenceTraceGraph?: IEvidenceTraceNode[];
  citationGrounding?: {
    totalCitationsCited?: number;
    groundedCitationsCount?: number;
    unverifiedCitationsCount?: number;
    groundingRatio?: number;
    isFullyGrounded?: boolean;
    groundedCases?: Array<{ caseTitle?: string; citation?: string; status?: string; corpusId?: string }>;
    unverifiedCases?: Array<{ caseTitle?: string; citation?: string; status?: string; warning?: string }>;
    disclaimer?: string;
  };
  generationMode?: string;
  llmModel?: string | null;
  requiresAdvocateReview?: boolean;
  prediction?: {
    status: string;
    estimatedOutcome: string;
    predictedDisposition?: string;
    predictedSuccessfulParty?: string;
    rationale: string;
    disclaimer: string;
    isExperimental?: boolean;
    predictionMode?: string;
    disposition?: string;
    successfulParty?: string;
    modelA?: any;
    modelB?: any;
    probabilities?: Record<string, number>;
    confidenceScore?: number;
    confidenceLevel?: string;
    modelVersion?: string;
  };
  researchNotes?: string;
  editedDrafts?: Record<string, string>;
  documentMetadata?: any;
  processingStatus: 'completed' | 'failed' | 'processing';
  createdAt: Date;
  updatedAt: Date;
}

const AnalysisSchema = new Schema<IAnalysis>(
  {
    userId: {
      type: Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true
    },
    caseId: {
      type: Schema.Types.ObjectId,
      ref: 'Case',
      index: true
    },
    caseTitle: {
      type: String,
      required: true
    },
    court: {
      type: String,
      default: 'Supreme Court of India'
    },
    category: {
      type: String,
      default: 'General'
    },
    inputTextSnippet: {
      type: String,
      required: true
    },
    caseUnderstanding: {
      type: Schema.Types.Mixed,
      default: {}
    },
    applicableLaw: {
      type: Schema.Types.Mixed,
      default: {}
    },
    extractedEntities: {
      type: Schema.Types.Mixed,
      default: {}
    },
    legalIssues: [{
      type: Schema.Types.Mixed
    }],
    similarCases: [{
      type: Schema.Types.Mixed
    }],
    legalArguments: [{
      type: Schema.Types.Mixed
    }],
    evidenceTraceGraph: [{
      type: Schema.Types.Mixed
    }],
    citationGrounding: {
      type: Schema.Types.Mixed
    },
    generationMode: {
      type: String,
      default: 'deterministic_offline'
    },
    llmModel: {
      type: String
    },
    requiresAdvocateReview: {
      type: Boolean,
      default: true
    },
    judicialTreatment: {
      type: Schema.Types.Mixed,
      default: {}
    },
    prediction: {
      type: Schema.Types.Mixed
    },
    researchNotes: {
      type: String,
      default: ''
    },
    editedDrafts: {
      type: Schema.Types.Mixed,
      default: {}
    },
    documentMetadata: {
      type: Schema.Types.Mixed
    },
    processingStatus: {
      type: String,
      enum: ['completed', 'failed', 'processing'],
      default: 'completed',
      index: true
    }
  },
  {
    timestamps: true
  }
);

AnalysisSchema.index({ userId: 1, createdAt: -1 });

export const Analysis = mongoose.models.Analysis || mongoose.model<IAnalysis>('Analysis', AnalysisSchema);
