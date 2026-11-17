# JURIST AI — REST API Contract

Base URL: `/api/v1`

All responses follow a uniform JSON structure:
```json
{
  "success": true,
  "message": "Optional descriptive status message",
  "data": {},
  "pagination": { "total": 100, "page": 1, "limit": 10, "totalPages": 10 }
}
```

---

## 1. Authentication Endpoints

### `POST /api/v1/auth/register`
Creates a new user account.
- **Request Body**:
  ```json
  { "name": "Adv. Ramesh", "email": "ramesh@law.in", "password": "SecurePassword123" }
  ```
- **Response** (201 Created):
  ```json
  {
    "success": true,
    "data": {
      "user": { "id": "...", "name": "Adv. Ramesh", "email": "ramesh@law.in", "role": "user" },
      "token": "eyJhbGciOi..."
    }
  }
  ```

### `POST /api/v1/auth/login`
Authenticates an existing user.
- **Request Body**:
  ```json
  { "email": "ramesh@law.in", "password": "SecurePassword123" }
  ```

### `GET /api/v1/auth/me`
Retrieves authenticated user profile. Requires Bearer Token.

---

## 2. Case Management Endpoints

### `POST /api/v1/cases`
Creates a draft or submitted case. Supports multipart/form-data with optional file attachment (`document`).
- **Form Fields**: `title`, `description`, `court`, `category`

### `GET /api/v1/cases`
Retrieves paginated user cases.
- **Query Params**: `page`, `limit`, `search`, `category`

### `GET /api/v1/cases/:id`
Retrieves specific case with document attachments.

---

## 3. Analysis & Precedent Retrieval Endpoints

### `POST /api/v1/analysis`
Executes complete NLP parsing, precedent retrieval, and outcome likelihood estimation.
- **Request Form/JSON**:
  ```json
  {
    "caseTitle": "Writ Petition on Telecommunication Tapping",
    "court": "Supreme Court of India",
    "category": "Constitutional Law",
    "description": "Challenging state interception without judicial warrant under Article 21..."
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "success": true,
    "data": {
      "id": "an_...",
      "caseTitle": "...",
      "extractedEntities": { "statutes": [...], "sections": [...], "legalTerms": [...] },
      "legalIssues": [{ "issue": "...", "confidenceScore": 0.95, "statutoryProvision": "..." }],
      "similarCases": [{ "caseTitle": "...", "similarityPercentage": 27.6, "citation": "...", "sourceUrl": "..." }],
      "prediction": { "estimatedOutcome": "Likely Allowed", "probabilities": { "Allowed": 0.82, "Dismissed": 0.18 } }
    }
  }
  ```

### `GET /api/v1/analysis`
Retrieves user analysis history with search and pagination.

### `GET /api/v1/analysis/:id`
Retrieves detailed analysis report.

---

## 4. Precedent Library Endpoints

### `GET /api/v1/precedents`
Publicly lists verified Indian court judgments.
- **Query Params**: `page`, `limit`, `search`, `category`, `court`

### `GET /api/v1/precedents/:id`
Retrieves full ratio decidendi and citation metadata for a precedent.

---

## 5. Saved Cases (Bookmarks)

### `POST /api/v1/saved-cases`
Bookmarks a precedent or analysis.
- **Request Body**: `{ precedentId, caseTitle, court, citation, sourceUrl, category }`

### `GET /api/v1/saved-cases`
Returns user bookmarked cases.

---

## 6. System Health

### `GET /api/v1/health`
Returns system component status, database connectivity, and ML engine version.
