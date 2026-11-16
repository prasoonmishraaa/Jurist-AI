import { LegalArgumentService } from '../src/services/argumentService';
import { LegislationService } from '../src/services/legislationService';
import { ISupportingJudgmentPassage, IEvidenceTraceNode } from '../src/models/Analysis';

describe('Feature 3.1: Legal Authority and Quotation Integrity Audit Test Suite', () => {
  // 1. Reject an invalid neutral citation format or mismatched citation
  it('1. rejects invalid neutral citation format and citation mismatches against verified authorities', () => {
    // Malformed neutral citation format (e.g. invalid string)
    const malformedCheck = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Random High Court Case',
      neutralCitation: 'INVALID-CITATION-1234'
    });
    expect(malformedCheck.isValid).toBe(false);
    expect(malformedCheck.errors.some(e => e.includes('Invalid neutral citation format'))).toBe(true);

    // Mismatched citation for Vihaan Kumar (e.g. old erroneous citation 2024 INSC 582 instead of 2025 INSC 162)
    const vihaanMismatch = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Vihaan Kumar v. State of Haryana',
      neutralCitation: '2024 INSC 582'
    });
    expect(vihaanMismatch.isValid).toBe(false);
    expect(vihaanMismatch.errors.some(e => e.includes('Neutral citation mismatch for "Vihaan Kumar'))).toBe(true);
    expect(vihaanMismatch.errors.some(e => e.includes('expected verified "2025 INSC 162"'))).toBe(true);

    // Mismatched citation for Prabir Purkayastha (e.g. 2024 INSC 412 instead of 2024 INSC 414)
    const prabirMismatch = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Prabir Purkayastha v. State (NCT of Delhi)',
      neutralCitation: '2024 INSC 412'
    });
    expect(prabirMismatch.isValid).toBe(false);
    expect(prabirMismatch.errors.some(e => e.includes('expected verified "2024 INSC 414"'))).toBe(true);

    // Valid neutral citations pass
    const validVihaan = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Vihaan Kumar v. State of Haryana',
      neutralCitation: '2025 INSC 162',
      paragraphNumber: 14,
      isDirectQuote: true,
      verbatimQuote: 'Thus, the requirement of informing the person arrested of the grounds of arrest is not a formality...',
      verificationStatus: 'character_verified'
    });
    expect(validVihaan.isValid).toBe(true);
    expect(validVihaan.errors.length).toBe(0);
  });

  // 2. Reject a paragraph number not supported by the source
  it('2. rejects paragraph numbers not supported by primary signed records', () => {
    // Navtej Singh Johar: claimed Para 268 instead of verified Para 267
    const navtejCheck = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Navtej Singh Johar and Ors. v. Union of India',
      neutralCitation: '2018 INSC 790',
      paragraphNumber: 268 // Invalid: primary record holds ratio in Para 267
    });
    expect(navtejCheck.isValid).toBe(false);
    expect(navtejCheck.errors.some(e => e.includes('Paragraph number not supported by source'))).toBe(true);
    expect(navtejCheck.errors.some(e => e.includes('claimed Para 268, but primary record verifies Para 267'))).toBe(true);

    // Shayara Bano: claimed Para 395 instead of verified Para 101 for Manifest Arbitrariness
    const shayaraCheck = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Shayara Bano v. Union of India',
      neutralCitation: '2017 INSC 615',
      paragraphNumber: 395 // Invalid: manifest arbitrariness doctrine is in Para 101
    });
    expect(shayaraCheck.isValid).toBe(false);
    expect(shayaraCheck.errors.some(e => e.includes('claimed Para 395, but primary record verifies Para 101'))).toBe(true);
  });

  // 3. Prevent editorial paraphrases from being displayed as direct quotations
  it('3. strictly prevents editorial paraphrases from claiming direct quotations or rendering verbatim quotes', () => {
    // Attempting to set isDirectQuote: true on an editorial paraphrase
    const invalidQuote = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'State of Haryana v. Bhajan Lal',
      editorialParaphrase: 'Laid down seven illustrative categories...',
      isDirectQuote: true,
      verbatimQuote: 'Laid down seven illustrative categories...',
      verificationStatus: 'editorial_paraphrase'
    });
    expect(invalidQuote.isValid).toBe(false);
    expect(invalidQuote.errors.some(e => e.includes('Editorial paraphrase cannot be claimed as a direct quotation'))).toBe(true);

    // Attempting to attach verbatimQuote when isDirectQuote is false
    const leakedVerbatim = LegalArgumentService.validateAuthorityPassage({
      caseTitle: 'Sample Case',
      isDirectQuote: false,
      verbatimQuote: 'Some quote text that should not appear in quotes'
    });
    expect(leakedVerbatim.isValid).toBe(false);
    expect(leakedVerbatim.errors.some(e => e.includes('When isDirectQuote is false, verbatimQuote must be omitted'))).toBe(true);

    // getSupportingJudgmentPassage strictly strips verbatimQuote if isDirectQuote is false
    const genericPassage = LegalArgumentService.getSupportingJudgmentPassage('NON_EXISTENT_CASE', 'Summary paraphrase');
    expect(genericPassage.isDirectQuote).toBe(false);
    expect(genericPassage.verbatimQuote).toBeUndefined();
    expect(genericPassage.verificationStatus).toBe('unverified');
  });

  // 4. Ensure unverified passages are visibly labelled
  it('4. ensures unverified passages are visibly labelled with verificationStatus: "unverified"', () => {
    // Arbitrary unverified precedent
    const unverifiedPassage = LegalArgumentService.getSupportingJudgmentPassage('SC-UNVERIFIED-001');
    expect(unverifiedPassage.verificationStatus).toBe('unverified');
    expect(unverifiedPassage.isDirectQuote).toBe(false);
    expect(unverifiedPassage.paragraphNumber).toBeUndefined();
    expect(unverifiedPassage.verbatimQuote).toBeUndefined();
    expect(unverifiedPassage.pinpointCitation).toBeUndefined();

    // Verified authorities return character_verified
    const vihaan = LegalArgumentService.getSupportingJudgmentPassage('SC-2025-026');
    expect(vihaan.verificationStatus).toBe('character_verified');
    expect(vihaan.isDirectQuote).toBe(true);
    expect(vihaan.paragraphNumber).toBe(14);
    expect(vihaan.verbatimQuote).toBeDefined();

    const prabir = LegalArgumentService.getSupportingJudgmentPassage('SC-2024-025');
    expect(prabir.verificationStatus).toBe('character_verified');
    expect(prabir.isDirectQuote).toBe(true);
    expect(prabir.paragraphNumber).toBe(21);
    expect(prabir.pinpointCitation).toContain('2024 INSC 414');

    const arnesh = LegalArgumentService.getSupportingJudgmentPassage('SC-2014-003');
    expect(arnesh.verificationStatus).toBe('character_verified');
    expect(arnesh.isDirectQuote).toBe(true);
    expect(arnesh.paragraphNumber).toBe(11);
    expect(arnesh.verbatimQuote).toContain('Our endeavour in this judgment');

    const lalita = LegalArgumentService.getSupportingJudgmentPassage('SC-2013-004');
    expect(lalita.verificationStatus).toBe('character_verified');
    expect(lalita.isDirectQuote).toBe(true);
    expect(lalita.paragraphNumber).toBe(120);
    expect(lalita.verbatimQuote).toContain('The registration of FIR is mandatory');

    const navtej = LegalArgumentService.getSupportingJudgmentPassage('SC-2018-005');
    expect(navtej.verificationStatus).toBe('character_verified');
    expect(navtej.isDirectQuote).toBe(true);
    expect(navtej.paragraphNumber).toBe(267);
    expect(navtej.pinpointCitation).toContain('Para 267');

    const shayara = LegalArgumentService.getSupportingJudgmentPassage('SC-2017-006');
    expect(shayara.verificationStatus).toBe('character_verified');
    expect(shayara.isDirectQuote).toBe(true);
    expect(shayara.paragraphNumber).toBe(101);
    expect(shayara.verbatimQuote).toContain('Manifest arbitrariness');

    const dkBasu = LegalArgumentService.getSupportingJudgmentPassage('SC-1996-012');
    expect(dkBasu.verificationStatus).toBe('character_verified');
    expect(dkBasu.isDirectQuote).toBe(true);
    expect(dkBasu.paragraphNumber).toBe(35);
    expect(dkBasu.verbatimQuote).toContain('The person arrested may be permitted to meet his lawyer');

    const bhajan = LegalArgumentService.getSupportingJudgmentPassage('SC-1990-009');
    expect(bhajan.verificationStatus).toBe('character_verified');
    expect(bhajan.isDirectQuote).toBe(true);
    expect(bhajan.paragraphNumber).toBe(102);
    expect(bhajan.verbatimQuote).toContain('Where the allegations made in the first information report');
  });

  // 5. Confirm evidence trace generation continues working end-to-end
  it('5. confirms end-to-end evidence trace generation operates reliably with audited authorities', () => {
    const rawFiling = `
      IN THE SUPREME COURT OF INDIA.
      Criminal Writ Petition No. 101 of 2025.
      The petitioner was arrested by the respondent police authorities on 12 January 2025 without communicating written grounds of arrest.
      The arrest is arbitrary and completely unconstitutional under Article 22(1) and Article 14.
    `;
    const law = LegislationService.assessApplicableLegislation(rawFiling, 'Criminal Law');
    const docMeta = {
      filename: 'petition.pdf',
      pageCount: 1,
      extractionMethod: 'native',
      overallStatus: 'SUCCESS',
      pages: [
        {
          pageNumber: 1,
          text: rawFiling,
          extractionMethod: 'native',
          status: 'SUCCESS',
          confidence: 1.0,
          warnings: []
        }
      ]
    };

    const understanding = LegalArgumentService.analyzeCaseFacts(
      rawFiling,
      'Criminal Law',
      'Supreme Court of India',
      law,
      docMeta
    );
    const questions = LegalArgumentService.buildQuestionsOfLaw(rawFiling, law, understanding);
    const matchedPrecedents = [
      {
        id: 'SC-2025-026',
        caseTitle: 'Vihaan Kumar v. State of Haryana and Anr.',
        citation: '2025 INSC 162',
        court: 'Supreme Court of India',
        judgmentDate: '2025-02-07',
        category: 'Criminal Law',
        legalProvisions: ['Article 22(1)'],
        summary: 'Mandatory written grounds of arrest',
        sourceUrl: 'https://main.sci.gov.in',
        officialSourceUrl: 'https://main.sci.gov.in/pdf/vihaan.pdf',
        officialSourceVerified: true,
        verificationStatus: 'verified_official',
        matchedTerms: ['grounds', 'arrest'],
        relevanceClassification: 'Directly relevant',
        retrievalReason: 'Grounds of arrest not communicated in writing',
        retrievalSignals: {
          tfidfRank: 1,
          bm25Rank: 1,
          rrfScore: 0.033,
          activeModalities: ['tfidf', 'bm25']
        }
      }
    ];

    const args = LegalArgumentService.generateLegalArguments(
      rawFiling,
      'Criminal Law',
      'Supreme Court of India',
      matchedPrecedents as any,
      understanding,
      law
    );

    const traceGraph = LegalArgumentService.buildEvidenceTraceGraph(
      understanding,
      questions,
      args,
      matchedPrecedents as any,
      law,
      docMeta
    );

    expect(traceGraph).toBeDefined();
    expect(traceGraph.length).toBeGreaterThan(0);

    const firstNode: IEvidenceTraceNode = traceGraph[0];
    expect(firstNode.traceId).toBeDefined();
    expect(firstNode.factAssertion).toBeDefined();
    expect(firstNode.statutoryProvision).toBeDefined();
    expect(firstNode.draftSubmissionSnippet).toBeDefined();
    expect(firstNode.confidenceAssessment).toBeDefined();

    // Verify judgment passage in the trace node
    if (firstNode.judgmentPassage) {
      expect(firstNode.judgmentPassage.verificationStatus).toBeDefined();
      if (firstNode.judgmentPassage.isDirectQuote) {
        expect(firstNode.judgmentPassage.verificationStatus).toBe('character_verified');
        expect(firstNode.judgmentPassage.verbatimQuote).toBeDefined();
        expect(firstNode.judgmentPassage.paragraphNumber).toBeDefined();
      }
    }
  });
});
