import axios from 'axios';
import { mlClient } from '../src/integrations/mlClient';
import { localInferenceEngine } from '../src/integrations/localInference';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('MLServiceClient — Hybrid Legal Retrieval Integration & Overwrite Fix', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('Feature 1: prefers and preserves Python hybrid precedents when Python returns valid results', async () => {
    const mockPythonPrecedents = [
      {
        id: 'SC-2013-004',
        caseTitle: 'Lalita Kumari v. Govt. of U.P. and Ors.',
        similarityScore: 0.95,
        matchedTerms: ['section 154', 'first information report'],
        retrievalSignals: {
          tfidf_rank: 1,
          bm25_rank: 1,
          semantic_rank: null,
          rrf_score: 0.032787,
          active_modalities: ['tfidf', 'bm25']
        }
      },
      {
        id: 'SC-1990-009',
        caseTitle: 'State of Haryana and Ors. v. Ch. Bhajan Lal and Ors.',
        similarityScore: 0.9347,
        matchedTerms: ['section 154', 'report'],
        retrievalSignals: {
          tfidf_rank: 2,
          bm25_rank: 2,
          semantic_rank: null,
          rrf_score: 0.032258,
          active_modalities: ['tfidf', 'bm25']
        }
      }
    ];

    mockedAxios.post.mockResolvedValueOnce({
      data: {
        cleanedTextSnippet: 'Police officer refuses to register FIR...',
        entities: [{ text: 'Section 154', label: 'STATUTE' }],
        legalIssues: ['Mandatory FIR registration'],
        precedents: mockPythonPrecedents,
        prediction: {
          status: 'qualitative_research_mode',
          estimatedOutcome: 'Structured Doctrinal & Authority Assessment'
        }
      }
    });

    const result = await mlClient.analyzeCase('Police officer refuses to register FIR under Section 154');

    expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    expect(result.precedents).toBeDefined();
    expect(result.precedents.length).toBe(2);

    // Verify Python results are PRESERVED and NOT overwritten by localInferenceEngine
    expect(result.precedents[0].id).toBe('SC-2013-004');
    expect(result.precedents[1].id).toBe('SC-1990-009');
    expect(result.precedents[0].retrievalSignals).toBeDefined();
    expect(result.precedents[0].retrievalSignals.rrf_score).toBe(0.032787);

    // Verify other analysis fields from Python remain intact
    expect(result.cleanedTextSnippet).toContain('Police officer refuses');
    expect(result.entities.length).toBe(1);
    expect(result.legalIssues).toEqual(['Mandatory FIR registration']);
  });

  it('falls back to TypeScript localInferenceEngine when Python service returns null or malformed precedents', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        cleanedTextSnippet: 'Some legal text...',
        entities: [],
        legalIssues: [],
        precedents: null // null / malformed from Python
      }
    });

    const result = await mlClient.analyzeCase('Arrest without furnishing written grounds of arrest');

    expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    expect(result.precedents).toBeDefined();
    // Should fallback to localInferenceEngine
    expect(result.precedents.length).toBeGreaterThan(0);
    expect(result.precedents[0].caseTitle).toBeDefined();
  });

  it('falls back to TypeScript localInferenceEngine when Python service returns empty precedents', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        cleanedTextSnippet: 'Some legal text...',
        entities: [],
        legalIssues: [],
        precedents: [] // empty from Python
      }
    });

    const result = await mlClient.analyzeCase('Arrest without furnishing written grounds of arrest');

    expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    expect(result.precedents).toBeDefined();
    // Should fallback to localInferenceEngine
    expect(result.precedents.length).toBeGreaterThan(0);
    expect(result.precedents[0].caseTitle).toBeDefined();
  });

  it('falls back to TypeScript localInferenceEngine when Python HTTP service times out or errors', async () => {
    mockedAxios.post.mockRejectedValueOnce(new Error('timeout of 3500ms exceeded'));

    const result = await mlClient.analyzeCase('Arrest without notice Article 22(1)');

    expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    expect(result.precedents).toBeDefined();
    expect(result.precedents.length).toBeGreaterThan(0);
    expect(result.prediction).toBeDefined();
    expect(result.entities).toBeDefined();
  });

  it('retrieveSimilar() preserves Python results when available and falls back on error', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        precedents: [
          { id: 'SC-2017-001', caseTitle: 'Justice K.S. Puttaswamy (Retd.) v. Union of India', similarityScore: 0.99 }
        ]
      }
    });

    const resSuccess = await mlClient.retrieveSimilar('Pegasus privacy Article 21', 5);
    expect(resSuccess.length).toBe(1);
    expect(resSuccess[0].id).toBe('SC-2017-001');

    mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));
    const resFallback = await mlClient.retrieveSimilar('Pegasus privacy Article 21', 5);
    expect(resFallback.length).toBeGreaterThan(0);
  });
});
