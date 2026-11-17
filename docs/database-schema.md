# JURIST AI — Database Schema & Data Models

Database Engine: MongoDB Atlas (M0 Free Tier)
ODM: Mongoose with TypeScript Schema Interfaces

---

## 1. User Model (`User`)

Stores researcher and advocate user accounts with bcrypt password hashes.
```typescript
interface IUser {
  name: string;
  email: string; // unique, lowercase, indexed
  passwordHash: string; // select: false
  role: 'user' | 'admin'; // default: 'user'
  createdAt: Date;
  updatedAt: Date;
}
```

## 2. Case Model (`Case`)

Stores drafted or uploaded legal cases with document metadata.
```typescript
interface ICase {
  userId: ObjectId; // ref: 'User', indexed
  title: string;
  description: string;
  court: string;
  category: string;
  uploadedDocuments: Array<{
    originalName: string;
    fileName: string;
    fileSize: number;
    mimeType: string;
    extractedTextSnippet?: string;
    uploadedAt: Date;
  }>;
  status: 'draft' | 'analyzed' | 'archived';
  createdAt: Date;
  updatedAt: Date;
}
```

## 3. Precedent Model (`Precedent`)

Stores genuine landmark Indian court decisions with traceable citations and official URLs.
```typescript
interface IPrecedent {
  caseTitle: string; // indexed
  court: string; // indexed
  judgmentDate: string; // indexed
  caseIdentifier: string;
  citation: string; // unique/indexed
  bench?: string;
  category: string; // indexed
  legalProvisions: string[];
  summary: string;
  judgmentText: string;
  sourceUrl: string;
  outcome?: 'Allowed' | 'Dismissed' | 'Partially Allowed' | 'Remanded';
  outcomeRationale?: string;
  verificationStatus: string; // default: 'verified_official'
  createdAt: Date;
}
```
**Compound Indexes**:
`{ caseTitle: 'text', judgmentText: 'text', summary: 'text' }`

## 4. Analysis Model (`Analysis`)

Stores immutable analysis snapshots containing NLP entities, matched precedents, and ML predictions.
```typescript
interface IAnalysis {
  userId: ObjectId; // ref: 'User', indexed
  caseId?: ObjectId; // ref: 'Case', indexed
  caseTitle: string;
  court: string;
  category: string;
  inputTextSnippet: string;
  extractedEntities: Record<string, any>;
  legalIssues: Array<{
    issue: string;
    statutoryProvision: string;
    confidenceScore: number;
    description: string;
    matchedKeywords: string[];
  }>;
  similarCases: Array<{
    caseTitle: string;
    court: string;
    citation: string;
    sourceUrl: string;
    similarityPercentage: number;
    matchedTerms: string[];
  }>;
  prediction: {
    status: string;
    estimatedOutcome: string;
    probabilities: { Allowed: number; Dismissed: number };
    confidenceLevel: 'High' | 'Moderate' | 'Low';
    rationale: string;
    modelVersion: string;
    disclaimer: string;
  };
  modelVersion: string;
  processingStatus: 'completed' | 'failed' | 'processing';
  createdAt: Date;
}
```

## 5. SavedCase Model (`SavedCase`)

Stores bookmarks and user-specific notes on precedent authorities.
```typescript
interface ISavedCase {
  userId: ObjectId; // ref: 'User', indexed
  precedentId?: ObjectId; // ref: 'Precedent'
  analysisId?: ObjectId; // ref: 'Analysis'
  caseTitle: string;
  court: string;
  citation: string;
  sourceUrl: string;
  category: string;
  notes?: string;
  createdAt: Date;
}
```
