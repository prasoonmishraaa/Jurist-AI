export interface User {
  id: string;
  name: string;
  email: string;
  role: 'user' | 'admin';
  createdAt?: string;
}

export interface LegalEntityItem {
  term: string;
  definition: string;
}

export interface ExtractedEntities {
  parties?: {
    petitioners: string[];
    respondents: string[];
  };
  courts?: string[];
  judges?: string[];
  statutes?: string[];
  sections?: string[];
  citations?: string[];
  legalTerms?: LegalEntityItem[];
  disclaimer?: string;
}

export interface LegalIssue {
  issue: string;
  relevantFacts?: string;
  statutoryProvision: string;
  supportingAuthorities?: string[];
  whyIssueMatters?: string;
  informationStillRequired?: string;
  description: string;
  matchedKeywords?: string[];
}

export type PrecedentRelevanceClass =
  | 'Directly relevant'
  | 'Supporting authority'
  | 'Constitutional background'
  | 'Distinguishing authority'
  | 'Potentially adverse authority'
  | 'Further research required';

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
  pageConfidence?: number | null;
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
  pinpointCitation?: string;
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

export interface IAttributedFact {
  id: string;
  statement: string;
  classification: 'User-provided fact' | 'Party allegation' | 'Material fact' | 'Unresolved';
  pageNumber?: number;
  extractionMethod?: 'native' | 'ocr' | 'unresolved';
  pageConfidence?: number | null;
  uncertainTokens?: string[];
  attributionStatus: 'verified' | 'unresolved' | 'unavailable';
  sourceSnippet?: string;
}

export interface Precedent {
  id?: string;
  _id?: string;
  caseTitle: string;
  court: string;
  judgmentDate: string;
  caseIdentifier?: string;
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
  verificationStatus?: string;
  verificationNote?: string;
  similarityScore?: number;
  matchedTerms?: string[];
  relevanceClassification?: PrecedentRelevanceClass;
  retrievalReason?: string;
  article141Status?: string;
  obiterAndScopeNote?: string;
  subsequentTreatment?: string;
  historicalOutcome?: string;
  outcomeRationale?: string;
  retrievalSignals?: IRetrievalSignalBreakdown;
  ratioPrinciple?: string;
}

export interface DetectedDateEntry {
  rawDate: string;
  parsedIso?: string;
  role: 'offence' | 'fir' | 'arrest' | 'remand' | 'filing' | 'unspecified';
  contextSnippet: string;
}

export interface ApplicableLawAssessment {
  isCriminalOrQuasiCriminal: boolean;
  regimeStatus:
    | 'post_july_2024_new_codes'
    | 'pre_july_2024_legacy_codes'
    | 'transitional_mixed'
    | 'uncertain_missing_dates'
    | 'civil_special_statute';
  regimeSummary: string;
  detectedDates: DetectedDateEntry[];
  missingDates: string[];
  substantiveLaw: Array<{
    provision: string;
    statute: string;
    applicabilityNote: string;
  }>;
  proceduralLaw: Array<{
    provision: string;
    statute: string;
    applicabilityNote: string;
  }>;
  evidenceLaw?: {
    statute: string;
    applicabilityNote: string;
  };
  transitionalNotes: string[];
  verificationRequired: string[];
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
  isCorpusGrounded?: boolean;
  verificationWarning?: string;
}

export interface ICounterArgument {
  opposingGround: string;
  opposingLegalBasis: string;
  factualBasis?: string;
  vulnerabilityAssessment: string;
  rebuttalStrategy: string;
  requiredEvidence: string;
}

export interface ILegalArgument {
  id: string;
  groundNumber: string;
  heading: string;
  legalQuestion?: string;
  legalProposition: string;
  relevantFacts: string;
  applicableProvisions: string[];
  supportingPrecedents: ISupportingPrecedent[];
  ratioDecidendi?: string;
  judicialReasoning: string;
  applicationToFacts: string;
  factualDistinctions?: string;
  suggestedSubmission: string;
  draftDisclaimer?: string;
  evidenceRequired?: string[];
  weaknesses?: string;
  limitations: string;
  counterarguments: ICounterArgument[];
  sourceTraceId?: string;
  ocrConfidenceWarning?: string;
  generationMode?: string;
  isAiGenerated?: boolean;
  requiresAdvocateReview?: boolean;
  isCitationGrounded?: boolean;
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
  factClassification?: {
    userProvidedFacts: string[];
    partyAllegations: string[];
    reasonableInferences: string[];
    missingInformation: string[];
    factsRequiringVerification: string[];
  };
  disputedActions: string[];
  allegedViolations: string[];
  missingInformation: string[];
  evidenceAudit?: IEvidenceAuditItem[];
  proceduralPosture?: {
    detectedPosture: string;
    custodyStatus:
      | 'in_custody_arrested'
      | 'apprehending_arrest'
      | 'released_on_bail'
      | 'civil_or_non_custodial'
      | 'unclear';
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

export interface IModelPredictionMeta {
  target: string;
  prediction: string;
  uncalibratedScores: Record<string, number>;
  confidenceScore: number;
  confidenceLevel: string;
  sampleSize: number;
  macroF1: number;
  classes: string[];
  domainLimitation?: string;
  abstained?: boolean;
  domainStatus?: string;
  rawPrediction?: string;
}

export interface QualitativeResearchMeta {
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
  modelA?: IModelPredictionMeta;
  modelB?: IModelPredictionMeta;
  probabilities?: Record<string, number>;
  confidenceScore?: number;
  confidenceLevel?: string;
  modelVersion?: string;
}

export interface CaseAnalysis {
  id: string;
  _id?: string;
  caseId?: string;
  caseTitle: string;
  court: string;
  category: string;
  inputTextSnippet: string;
  caseUnderstanding?: ICaseUnderstanding;
  applicableLaw?: ApplicableLawAssessment;
  extractedEntities: ExtractedEntities;
  legalIssues: LegalIssue[];
  similarCases: Precedent[];
  legalArguments?: ILegalArgument[];
  judicialTreatment?: IJudicialTreatmentAssessment;
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
  documentMetadata?: any;
  prediction?: QualitativeResearchMeta;
  researchNotes?: string;
  editedDrafts?: Record<string, string>;
  persistenceMode?: 'mongodb' | 'in_memory_fallback';
  processingStatus: 'completed' | 'failed' | 'processing';
  createdAt: string;
  updatedAt?: string;
}

export interface SavedCase {
  id: string;
  _id?: string;
  precedentId?: string;
  precedentCode?: string;
  analysisId?: string;
  caseTitle: string;
  court: string;
  citation: string;
  officialSourceUrl?: string;
  officialSourceVerified?: boolean;
  secondaryReferenceUrl?: string;
  sourceUrl: string;
  verificationStatus?: string;
  category: string;
  notes?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface CorpusStatistics {
  totalJudgments: number;
  indexedPassages: number;
  landmarkJudgments: number;
  officialVerifiedLandmarks: number;
  secondaryReferences: number;
  openIndiaLawJudgments: number;
  databaseSyncedRecords: number;
  retrievalEngine: string;
  manifestVersion: string;
  activeModalities: string[];
  semanticModel?: string;
  isMlServiceConnected: boolean;
}

export interface SystemStats {
  totalUsers: number;
  totalCases: number;
  totalAnalyses: number;
  precedentCorpusCount: number;
  hybridCorpusCount?: number;
  indexedPassages?: number;
  officialVerifiedSourceCount?: number;
  secondaryReferenceCount?: number;
  openIndiaLawCount?: number;
  databaseSyncedCount?: number;
  corpusStats?: CorpusStatistics;
  persistenceMode?: string;
  database: {
    isConnected: boolean;
    state: number;
    host: string;
    persistenceMode?: string;
  };
  mlService: {
    pythonService: any;
    localEngine: string;
  };
}
