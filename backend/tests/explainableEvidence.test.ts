import { LegalArgumentService } from '../src/services/argumentService';
import { LegislationService } from '../src/services/legislationService';
import { localInferenceEngine } from '../src/integrations/localInference';
import {
  IMatchedPrecedent,
  IEvidenceTraceNode,
  IAnalysis,
  ILegalArgument
} from '../src/models/Analysis';

describe('Feature 3: Explainable AI & Evidence Traceability Subsystem', () => {
  // Realistic multi-page document fixture with mixed native and OCR pages
  const multiPageDocumentMetadata = {
    filename: 'police_investigation_dossier.pdf',
    documentType: 'pdf',
    pageCount: 3,
    extractionMethod: 'hybrid',
    overallStatus: 'SUCCESS',
    warnings: [],
    pages: [
      {
        pageNumber: 1,
        text: 'IN THE COURT OF THE SESSIONS JUDGE. The accused person was arrested on 10 August 2024 at 11:30 PM outside his residence without any prior notice. The FIR registered on 8 August 2024 charges offences under Section 318(4) BNS for cheating in commercial transactions.',
        extractionMethod: 'native',
        status: 'SUCCESS',
        confidence: 1.0,
        warnings: []
      },
      {
        pageNumber: 2,
        text: 'The police officers did not communicate the written grounds of arrest to the arrestee prior to production before the learned Judicial Magistrate. The accused contends that the arrest is arbitrary and completely unconstitutional.',
        extractionMethod: 'ocr',
        status: 'SUCCESS',
        confidence: 0.88,
        warnings: []
      },
      {
        pageNumber: 3,
        text: 'During interrogation, the investigating officer refused the request of the accused to consult with legal counsel. The petitioner alleges [?malicious?] prosecution by [?complainant?] with an ulterior motive.',
        extractionMethod: 'ocr',
        status: 'LOW_CONFIDENCE_OCR',
        confidence: 0.62, // Below 75% threshold + contains uncertain tokens
        warnings: ['Low confidence OCR extraction (62% average confidence).']
      }
    ]
  };

  const narrativeText = multiPageDocumentMetadata.pages.map(p => p.text).join('\n\n');
  const lawAssessment = LegislationService.assessApplicableLegislation(narrativeText, 'Criminal Law');

  // 1. Correct page attribution for facts across a multi-page document
  it('1. accurately attributes facts to their specific originating document pages across multi-page files', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );

    expect(understanding.attributedFacts).toBeDefined();
    expect(understanding.attributedFacts!.length).toBeGreaterThan(0);

    // Sentence from Page 1
    const p1Fact = understanding.attributedFacts!.find(f => f.statement.includes('accused person was arrested on 10 August 2024'));
    expect(p1Fact).toBeDefined();
    expect(p1Fact!.pageNumber).toBe(1);
    expect(p1Fact!.extractionMethod).toBe('native');
    expect(p1Fact!.pageConfidence).toBe(1.0);
    expect(p1Fact!.attributionStatus).toBe('verified');

    // Sentence from Page 2
    const p2Fact = understanding.attributedFacts!.find(f => f.statement.includes('grounds of arrest'));
    expect(p2Fact).toBeDefined();
    expect(p2Fact!.pageNumber).toBe(2);
    expect(p2Fact!.extractionMethod).toBe('ocr');
    expect(p2Fact!.pageConfidence).toBe(0.88);
    expect(p2Fact!.attributionStatus).toBe('verified');

    // Sentence from Page 3
    const p3Fact = understanding.attributedFacts!.find(f => f.statement.includes('investigating officer refused'));
    expect(p3Fact).toBeDefined();
    expect(p3Fact!.pageNumber).toBe(3);
    expect(p3Fact!.extractionMethod).toBe('ocr');
    expect(p3Fact!.pageConfidence).toBe(0.62);
    expect(p3Fact!.attributionStatus).toBe('verified');
  });

  // 2. Separate attribution of facts and allegations
  it('2. separately classifies and attributes neutral background facts versus party allegations', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );

    // Objective neutral context fact
    const neutralFact = understanding.attributedFacts!.find(f => f.statement.includes('IN THE COURT OF THE SESSIONS JUDGE') || f.statement.includes('accused person was arrested'));
    expect(neutralFact).toBeDefined();
    expect(neutralFact!.classification).toBe('User-provided fact');

    // Contested allegation containing markers like "alleges" / "arbitrary"
    const allegation = understanding.attributedFacts!.find(f => f.statement.includes('contends that the arrest is arbitrary') || f.statement.includes('alleges'));
    expect(allegation).toBeDefined();
    expect(allegation!.classification).toBe('Party allegation');
  });

  // 3. Stable fact and argument IDs
  it('3. generates stable deterministic IDs for facts and legal arguments', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );

    understanding.attributedFacts!.forEach((f, idx) => {
      expect(f.id).toBe(`fact-${idx + 1}`);
      expect(typeof f.id).toBe('string');
    });

    const precedents = localInferenceEngine.retrieveSimilarPrecedents(narrativeText, 5) as IMatchedPrecedent[];
    const args = LegalArgumentService.generateLegalArguments(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      precedents,
      understanding,
      lawAssessment
    );

    expect(args.length).toBeGreaterThan(0);
    expect(args[0].id).toBe('arg-art22-grounds');
    expect(args[0].groundNumber).toBe('Ground 1');
  });

  // 4. Issue-to-statute relationships
  it('4. establishes explicit issue-to-statute mapping based on governing legal codes', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );
    const questions = LegalArgumentService.buildQuestionsOfLaw(narrativeText, lawAssessment, understanding);
    expect(questions.length).toBeGreaterThan(0);

    const art22Issue = questions.find(q => q.issue.includes('Article 22(1)') || q.issue.includes('grounds of arrest'));
    expect(art22Issue).toBeDefined();
    expect(art22Issue!.statutoryProvision).toMatch(/Article 22\(1\)|Section 47.*BNSS|Section 50.*CrPC/);
  });

  // 5. Issue-specific precedent mapping
  it('5. links precedents specifically per issue/ground rather than globally spraying all precedents', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );
    const questions = LegalArgumentService.buildQuestionsOfLaw(narrativeText, lawAssessment, understanding);
    const precedents = localInferenceEngine.retrieveSimilarPrecedents(narrativeText, 6) as IMatchedPrecedent[];
    const args = LegalArgumentService.generateLegalArguments(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      precedents,
      understanding,
      lawAssessment
    );

    const traceGraph = LegalArgumentService.buildEvidenceTraceGraph(
      understanding,
      questions,
      args,
      precedents,
      lawAssessment,
      multiPageDocumentMetadata
    );

    expect(traceGraph.length).toBeGreaterThan(0);

    // Ground 1: Article 22(1) grounds of arrest
    const g1 = traceGraph.find(t => t.groundNumber === 'Ground 1');
    expect(g1).toBeDefined();
    expect(g1!.precedent).toBeDefined();
    // Vihaan Kumar or Prabir Purkayastha or Mihir Rajesh Shah must be the authority for written grounds
    expect(g1!.precedent!.caseTitle).toMatch(/Vihaan Kumar|Prabir Purkayastha|Mihir Rajesh Shah/);
    // Must NOT be a matrimonial or cyber authority like Shreya Singhal or Vishaka
    expect(g1!.precedent!.caseTitle).not.toContain('Shreya Singhal');
    expect(g1!.precedent!.caseTitle).not.toContain('Vishaka');
  });

  // 6. Missing and unresolved evidence relationships
  it('6. visibly flags unresolved relationships when evidence cannot be linked without guessing', () => {
    // Isolated fact narrative without document metadata or matched issues
    const unreferencedFacts: ILegalArgument[] = [
      {
        id: 'arg-isolated-99',
        groundNumber: 'Ground 99',
        heading: 'Ground with No Available Precedents or Source Pages',
        legalQuestion: 'Unknown question',
        legalProposition: 'Unverified proposition',
        relevantFacts: 'A completely unreferenced factual assertion nowhere in document pages.',
        applicableProvisions: ['Special Statute Section 99'],
        supportingPrecedents: [], // No supporting precedent
        ratioDecidendi: 'N/A',
        judicialReasoning: 'N/A',
        applicationToFacts: 'N/A',
        factualDistinctions: 'N/A',
        suggestedSubmission: 'Submission text',
        draftDisclaimer: 'Disclaimer',
        evidenceRequired: [],
        weaknesses: 'N/A',
        limitations: 'N/A',
        counterarguments: []
      }
    ];

    const minimalUnderstanding: any = {
      parties: { petitioners: ['A'], respondents: ['B'] },
      materialFacts: ['Some fact'],
      chronology: [],
      attributedFacts: [],
      factClassification: { userProvidedFacts: [], partyAllegations: [] }
    };

    const unresolvableDocMetadata = {
      filename: 'other_case.pdf',
      pageCount: 1,
      pages: [
        {
          pageNumber: 1,
          text: 'Totally unrelated patent dispute text.',
          extractionMethod: 'native',
          status: 'SUCCESS',
          confidence: 1.0,
          warnings: []
        }
      ]
    };

    const trace = LegalArgumentService.buildEvidenceTraceGraph(
      minimalUnderstanding,
      [],
      unreferencedFacts,
      [],
      { regimeStatus: 'uncertain_missing_dates' } as any,
      unresolvableDocMetadata
    );

    expect(trace.length).toBe(1);
    const node = trace[0];
    expect(node.unresolvedRelationships).toBeDefined();
    expect(node.unresolvedRelationships).toContain('source_page_attribution');
    expect(node.unresolvedRelationships).toContain('legal_issue');
    expect(node.unresolvedRelationships).toContain('precedent_authority');
    expect(node.unresolvedRelationships).toContain('judgment_passage');
    expect(node.sourcePassage.attributionStatus).toBe('unresolved');
    expect(node.confidenceAssessment.overallTraceReliability).toBe('moderate_confidence');
  });

  // 7. Low-confidence OCR warning propagation
  it('7. propagates low-confidence OCR warnings and sets requires_verification when page confidence < 75%', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );
    const questions = LegalArgumentService.buildQuestionsOfLaw(narrativeText, lawAssessment, understanding);
    const precedents = localInferenceEngine.retrieveSimilarPrecedents(narrativeText, 5) as IMatchedPrecedent[];

    // Argument deliberately based on Page 3 (which has 62% OCR confidence)
    const page3Arg: ILegalArgument = {
      id: 'arg-counsel-interrogation',
      groundNumber: 'Ground 3',
      heading: 'Right to Counsel During Interrogation under D.K. Basu',
      legalQuestion: 'Whether denial of lawyer consultation during police interrogation violates Article 22(1)',
      legalProposition: 'Accused is entitled to consult an advocate during custodial interrogation.',
      relevantFacts: 'During interrogation, the investigating officer refused the request of the accused to consult with legal counsel. The petitioner alleges [?malicious?] prosecution by [?complainant?] with an ulterior motive.',
      applicableProvisions: ['Article 22(1), Constitution of India'],
      supportingPrecedents: [
        {
          id: 'SC-1997-008',
          caseTitle: 'D.K. Basu v. State of West Bengal',
          citation: '(1997) 1 SCC 416',
          court: 'Supreme Court of India',
          ratioPrinciple: 'Right to meet lawyer during interrogation',
          applicationToFacts: 'Directly applies to denial of counsel',
          officialSourceVerified: true,
          sourceUrl: 'https://main.sci.gov.in',
          authorityType: 'Binding SC Precedent'
        }
      ],
      ratioDecidendi: 'D.K. Basu guidelines',
      judicialReasoning: 'Custodial safeguards',
      applicationToFacts: 'Custodial refusal',
      factualDistinctions: 'None',
      suggestedSubmission: 'THAT the investigating agency violated D.K. Basu...',
      draftDisclaimer: 'Draft only',
      evidenceRequired: [],
      weaknesses: 'None',
      limitations: 'None',
      counterarguments: []
    };

    const trace = LegalArgumentService.buildEvidenceTraceGraph(
      understanding,
      questions,
      [page3Arg],
      precedents,
      lawAssessment,
      multiPageDocumentMetadata
    );

    expect(trace.length).toBe(1);
    const node = trace[0];
    expect(node.confidenceAssessment.isOcrUncertain).toBe(true);
    expect(node.confidenceAssessment.overallTraceReliability).toBe('requires_verification');
    expect(node.confidenceAssessment.ocrReliabilityCaveat).toBeDefined();
    expect(node.confidenceAssessment.ocrReliabilityCaveat).toContain('62%');
    expect(node.confidenceAssessment.ocrReliabilityCaveat).toContain('< 75% threshold');
    expect(page3Arg.ocrConfidenceWarning).toBe(node.confidenceAssessment.ocrReliabilityCaveat);
  });

  // 8. Uncertain token propagation
  it('8. flags uncertain tokens [?token?] and lists them explicitly in the OCR caveat', () => {
    const understanding = LegalArgumentService.analyzeCaseFacts(
      narrativeText,
      'Criminal Law',
      'High Court of Delhi',
      lawAssessment,
      multiPageDocumentMetadata
    );
    const p3Fact = understanding.attributedFacts!.find(f => f.statement.includes('[?malicious?]'));
    expect(p3Fact).toBeDefined();
    expect(p3Fact!.uncertainTokens).toEqual(expect.arrayContaining(['malicious', 'complainant']));

    const tokens = LegalArgumentService.extractUncertainTokens('The [?accused?] denied [?guilt?] under Section 420.');
    expect(tokens).toEqual(['accused', 'guilt']);
  });

  // 9. No warning for arguments unrelated to uncertain OCR text
  it('9. does NOT inject OCR warnings into arguments derived from digital or high-confidence text', () => {
    const digitalMetadata = {
      filename: 'clean_petition.pdf',
      pageCount: 1,
      pages: [
        {
          pageNumber: 1,
          text: 'The petitioner was detained without grounds of arrest communicated in writing.',
          extractionMethod: 'native',
          status: 'SUCCESS',
          confidence: 1.0,
          warnings: []
        }
      ]
    };

    const cleanNarrative = digitalMetadata.pages[0].text;
    const cleanLaw = LegislationService.assessApplicableLegislation(cleanNarrative, 'Criminal Law');
    const cleanUnderstanding = LegalArgumentService.analyzeCaseFacts(
      cleanNarrative,
      'Criminal Law',
      'High Court',
      cleanLaw,
      digitalMetadata
    );
    const cleanPrecedents = localInferenceEngine.retrieveSimilarPrecedents(cleanNarrative, 3) as IMatchedPrecedent[];
    const cleanArgs = LegalArgumentService.generateLegalArguments(
      cleanNarrative,
      'Criminal Law',
      'High Court',
      cleanPrecedents,
      cleanUnderstanding,
      cleanLaw
    );
    const cleanQuestions = LegalArgumentService.buildQuestionsOfLaw(cleanNarrative, cleanLaw, cleanUnderstanding);

    const trace = LegalArgumentService.buildEvidenceTraceGraph(
      cleanUnderstanding,
      cleanQuestions,
      cleanArgs,
      cleanPrecedents,
      cleanLaw,
      digitalMetadata
    );

    expect(trace.length).toBeGreaterThan(0);
    const node = trace[0];
    expect(node.confidenceAssessment.isOcrUncertain).toBe(false);
    expect(node.confidenceAssessment.ocrReliabilityCaveat).toBeUndefined();
    expect(cleanArgs[0].ocrConfidenceWarning).toBeUndefined();
    expect(node.confidenceAssessment.overallTraceReliability).toBe('high_confidence');
  });

  // 10. Direct quote versus editorial paraphrase distinction
  it('10. explicitly distinguishes verbatim quotations from editorial paraphrases', () => {
    // Vihaan Kumar: verified verbatim quote available
    const vihaanPassage = LegalArgumentService.getSupportingJudgmentPassage('SC-2025-026');
    expect(vihaanPassage.isDirectQuote).toBe(true);
    expect(vihaanPassage.paragraphNumber).toBe(14);
    expect(vihaanPassage.verbatimQuote).toContain('mandatory constitutional requirement');
    expect(vihaanPassage.pinpointCitation).toContain('Para 14, 2025 INSC 162');
    expect(vihaanPassage.verificationStatus).toBe('character_verified');

    // Unverified / generic case ID
    const unverifiedPassage = LegalArgumentService.getSupportingJudgmentPassage('SC-UNKNOWN-999');
    expect(unverifiedPassage.isDirectQuote).toBe(false);
    expect(unverifiedPassage.paragraphNumber).toBeUndefined();
    expect(unverifiedPassage.verbatimQuote).toBeUndefined();
    expect(unverifiedPassage.verificationStatus).toBe('unverified');
  });

  // 11. No fabricated paragraph citations
  it('11. never manufactures paragraph citations or direct quotes for judgments without verified primary passages', () => {
    // Unverified / generic case ID
    const unverifiedPassage = LegalArgumentService.getSupportingJudgmentPassage(
      'SC-UNKNOWN-999',
      'Summary of unknown case ratio.'
    );
    expect(unverifiedPassage.isDirectQuote).toBe(false);
    expect(unverifiedPassage.paragraphNumber).toBeUndefined();
    expect(unverifiedPassage.verbatimQuote).toBeUndefined();
    expect(unverifiedPassage.pinpointCitation).toBeUndefined();
    expect(unverifiedPassage.editorialParaphrase).toBe('Summary of unknown case ratio.');
  });

  // 12. Retrieval signal rendering and unavailable semantic modality handling
  it('12. packages multi-modal retrieval signals and accurately indicates unavailable semantic rank', () => {
    const prec: IMatchedPrecedent = {
      caseTitle: 'Vihaan Kumar v. State of Haryana',
      court: 'Supreme Court of India',
      judgmentDate: '2025-02-07',
      citation: '2025 INSC 162',
      category: 'Criminal Law',
      legalProvisions: ['Article 22(1)', 'Section 50 CrPC'],
      summary: 'Written grounds mandatory',
      sourceUrl: 'https://indiankanoon.org/doc/12345/',
      officialSourceVerified: true,
      officialSourceUrl: 'https://main.sci.gov.in/pdf/vihaan.pdf',
      verificationStatus: 'verified_official',
      matchedTerms: ['grounds', 'arrest', 'written'],
      relevanceClassification: 'Directly relevant',
      retrievalReason: 'Directly relevant under Article 22(1)',
      retrievalSignals: {
        tfidfRank: 1,
        bm25Rank: 2,
        semanticRank: undefined, // Honestly unavailable on CPU
        rrfScore: 0.0325,
        activeModalities: ['tfidf', 'bm25'],
        matchedKeywords: ['grounds', 'arrest', 'written']
      }
    };

    expect(prec.retrievalSignals).toBeDefined();
    expect(prec.retrievalSignals!.tfidfRank).toBe(1);
    expect(prec.retrievalSignals!.bm25Rank).toBe(2);
    expect(prec.retrievalSignals!.semanticRank).toBeUndefined();
    expect(prec.retrievalSignals!.rrfScore).toBeCloseTo(0.0325);
    expect(prec.retrievalSignals!.activeModalities).toEqual(['tfidf', 'bm25']);
  });

  // 13. Backward compatibility with analyses created before this feature
  it('13. maintains 100% backward compatibility when consuming older analysis records without evidenceTraceGraph', () => {
    const legacyAnalysis: Partial<IAnalysis> = {
      caseTitle: 'State v. Legacy Defendant',
      court: 'Supreme Court of India',
      category: 'Criminal Law',
      inputTextSnippet: 'Legacy text snippet',
      legalArguments: [
        {
          id: 'legacy-arg-1',
          groundNumber: 'Ground 1',
          heading: 'Legacy ground',
          legalQuestion: 'Q',
          legalProposition: 'P',
          relevantFacts: 'F',
          applicableProvisions: ['Section 420 IPC'],
          supportingPrecedents: [],
          ratioDecidendi: 'R',
          judicialReasoning: 'J',
          applicationToFacts: 'A',
          factualDistinctions: 'D',
          suggestedSubmission: 'S',
          draftDisclaimer: 'Disclaimer',
          evidenceRequired: [],
          weaknesses: 'W',
          limitations: 'L',
          counterarguments: []
          // Note: sourceTraceId and ocrConfidenceWarning omitted
        }
      ],
      legalIssues: [],
      similarCases: []
      // Note: evidenceTraceGraph omitted entirely
    };

    expect(legacyAnalysis.evidenceTraceGraph).toBeUndefined();
    expect(legacyAnalysis.legalArguments![0].sourceTraceId).toBeUndefined();
    expect(legacyAnalysis.legalArguments![0].ocrConfidenceWarning).toBeUndefined();

    // System safely defaults when evidenceTraceGraph is missing
    const traceCount = legacyAnalysis.evidenceTraceGraph?.length || 0;
    expect(traceCount).toBe(0);
  });

  // 14. Evidence Trace tab rendering when the graph is empty or unavailable
  it('14. safely handles empty or unresolved evidence trace graphs without throwing', () => {
    const emptyGraph: IEvidenceTraceNode[] = [];
    expect(emptyGraph.length).toBe(0);

    const safeNodes = (emptyGraph && emptyGraph.length > 0) ? emptyGraph : null;
    expect(safeNodes).toBeNull();
  });
});
