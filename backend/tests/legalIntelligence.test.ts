import { AnalysisService } from '../src/services/analysisService';
import { mlClient } from '../src/integrations/mlClient';
import { LegalArgumentService } from '../src/services/argumentService';

describe('Feature: AI-Powered Legal Intelligence & Citation Grounding Integration', () => {
  const testUserId = 'user_test_intel_001';

  it('generates structured legal intelligence with questions of law, counterarguments, and evidence audit', async () => {
    const input = {
      caseTitle: 'Writ Petition: Challenge to Unlawful Arrest and Remand without Written Grounds',
      court: 'High Court of Delhi',
      category: 'Criminal Writ',
      description:
        'The petitioner was arrested on 14.10.2024 at 11:30 PM by police in connection with FIR No. 102/2024 under Section 318(4) BNS. No notice under Section 35(3) BNSS was served prior to arrest. Furthermore, no written grounds of arrest were communicated to the petitioner prior to production before the Judicial Magistrate, violating Article 22(1) of the Constitution.'
    };

    const result = await AnalysisService.performAnalysis(testUserId, input);

    expect(result).toBeDefined();
    expect(result.caseTitle).toBe(input.caseTitle);

    // 1. Procedural posture & custody intelligence
    expect(result.caseUnderstanding).toBeDefined();
    expect(result.caseUnderstanding.proceduralPosture).toBeDefined();
    expect(result.caseUnderstanding.proceduralPosture.custodyStatus).toBe('in_custody_arrested');

    // 2. Fact classification
    expect(result.caseUnderstanding.factClassification).toBeDefined();
    expect(result.caseUnderstanding.factClassification.userProvidedFacts.length).toBeGreaterThan(0);
    expect(result.caseUnderstanding.factClassification.factsRequiringVerification.length).toBeGreaterThan(0);

    // 3. Evidence Audit (Strictly "Document to obtain / verify")
    expect(Array.isArray(result.caseUnderstanding.evidenceAudit)).toBe(true);
    expect(result.caseUnderstanding.evidenceAudit.length).toBeGreaterThan(0);
    for (const item of result.caseUnderstanding.evidenceAudit) {
      expect(item.status).toBe('Document to obtain / verify');
      expect(item.documentName).toBeDefined();
      expect(item.purpose).toBeDefined();
    }

    // 4. Questions of law
    expect(Array.isArray(result.legalIssues)).toBe(true);
    expect(result.legalIssues.length).toBeGreaterThan(0);
    const hasArrestOrGroundsIssue = result.legalIssues.some(
      (iss: any) =>
        (iss.issue || '').toLowerCase().includes('grounds of arrest') ||
        (iss.issue || '').toLowerCase().includes('written grounds') ||
        (iss.issue || '').toLowerCase().includes('arrest')
    );
    expect(hasArrestOrGroundsIssue).toBe(true);

    // 5. Legal arguments & opposing counsel counterarguments
    expect(Array.isArray(result.legalArguments)).toBe(true);
    expect(result.legalArguments.length).toBeGreaterThan(0);

    const firstArg = result.legalArguments[0];
    expect(firstArg.groundNumber).toBeDefined();
    expect(firstArg.heading).toBeDefined();
    expect(firstArg.suggestedSubmission).toBeDefined();
    expect(firstArg.draftDisclaimer).toBeDefined();
    expect(Array.isArray(firstArg.counterarguments)).toBe(true);
    expect(firstArg.counterarguments.length).toBeGreaterThan(0);

    const firstCounter = firstArg.counterarguments[0];
    expect(firstCounter.opposingGround).toBeDefined();
    expect(firstCounter.opposingLegalBasis).toBeDefined();
    expect(firstCounter.factualBasis).toBeDefined();
    expect(firstCounter.rebuttalStrategy).toBeDefined();

    // 6. Evidence trace graph
    expect(Array.isArray(result.evidenceTraceGraph)).toBe(true);
    expect(result.evidenceTraceGraph.length).toBeGreaterThan(0);
    const firstTrace = result.evidenceTraceGraph[0];
    expect(firstTrace.traceId).toBeDefined();
    expect(firstTrace.groundNumber).toBeDefined();
    expect(firstTrace.sourcePassage).toBeDefined();

    // 7. Generation metadata & Advocate Review flag
    expect(result.requiresAdvocateReview).toBe(true);
    expect(result.generationMode).toBeDefined();
    expect(['gemini_direct', 'openai_direct', 'deterministic_offline', 'typescript_local_fallback']).toContain(
      result.generationMode
    );

    // 8. Model A & Model B outcome prediction preserved
    expect(result.prediction).toBeDefined();
  });

  it('gracefully falls back to local engine if Python service is offline without crashing', async () => {
    // Force invalid baseUrl to simulate network failure
    const originalClient = (mlClient as any).baseUrl;
    (mlClient as any).baseUrl = 'http://127.0.0.1:9999'; // unreachable port

    try {
      const input = {
        caseTitle: 'Cheque Dishonour Pleading',
        court: 'Chief Judicial Magistrate',
        category: 'Negotiable Instruments Act',
        description: 'Notice under Section 138 NI Act was served on drawer for cheque of Rs. 5,00,000 returned unpaid.'
      };

      const result = await AnalysisService.performAnalysis(testUserId, input);
      expect(result).toBeDefined();
      expect(result.legalArguments.length).toBeGreaterThan(0);
      expect(result.generationMode).toBe('typescript_local_fallback');
      expect(result.requiresAdvocateReview).toBe(true);
      expect(result.similarCases.length).toBeGreaterThan(0);
    } finally {
      (mlClient as any).baseUrl = originalClient;
    }
  });

  it('verifies TypeScript fallback domain coverage and schema compatibility when Python is offline', async () => {
    const originalClient = (mlClient as any).baseUrl;
    (mlClient as any).baseUrl = 'http://127.0.0.1:9999';

    try {
      // 1. Post-July 2024 Criminal Arrest Fallback Scenario
      const criminalPostJulyInput = {
        caseTitle: 'Bail Application — Post July 2024 Arrest without Written Grounds',
        court: 'High Court of Delhi',
        category: 'Criminal Law',
        description:
          'On 15 August 2024, FIR was registered under Section 318(4) BNS. Accused was arrested on 20 August 2024 without notice under Section 35(3) BNSS and grounds of arrest under Article 22(1) were not furnished.'
      };

      const crimResult = await AnalysisService.performAnalysis(testUserId, criminalPostJulyInput);
      expect(crimResult.generationMode).toBe('typescript_local_fallback');
      expect(crimResult.legalArguments.length).toBeGreaterThanOrEqual(2);

      // Verify Ground 1 respects post-transition BNSS
      const g1 = crimResult.legalArguments.find((a: any) => a.id === 'arg-art22-grounds');
      expect(g1).toBeDefined();
      expect(g1!.applicableProvisions.join(' ')).toContain('BNSS');
      expect(g1!.applicableProvisions.join(' ')).not.toContain('CrPC');

      // Verify full frontend schema compatibility on fallback objects
      for (const arg of crimResult.legalArguments) {
        expect(arg.id).toBeDefined();
        expect(arg.groundNumber).toBeDefined();
        expect(arg.heading).toBeDefined();
        expect(arg.legalQuestion).toBeDefined();
        expect(arg.legalProposition).toBeDefined();
        expect(arg.relevantFacts).toBeDefined();
        expect(Array.isArray(arg.applicableProvisions)).toBe(true);
        expect(Array.isArray(arg.supportingPrecedents)).toBe(true);
        expect(arg.ratioDecidendi).toBeDefined();
        expect(arg.judicialReasoning).toBeDefined();
        expect(arg.applicationToFacts).toBeDefined();
        expect(arg.suggestedSubmission).toBeDefined();
        expect(arg.draftDisclaimer).toBeDefined();
        expect(Array.isArray(arg.counterarguments)).toBe(true);
        expect(arg.counterarguments.length).toBeGreaterThan(0);
        for (const ca of arg.counterarguments) {
          expect(ca.opposingGround).toBeDefined();
          expect(ca.opposingLegalBasis).toBeDefined();
          expect(ca.factualBasis).toBeDefined();
          expect(ca.rebuttalStrategy).toBeDefined();
        }
      }

      // 2. Commercial / Civil Dispute Quashing Fallback Scenario
      const quashingInput = {
        caseTitle: 'Quashing Petition — Commercial Supply Contract Dispute',
        court: 'High Court of Bombay',
        category: 'Criminal Law',
        description:
          'Civil commercial dispute regarding delivery of raw materials under supply agreement dated 10 January 2023. Buyer defaulted on payment; seller filed criminal complaint alleging cheating under Section 420 IPC. Petitioner seeks quashing of FIR under Section 482 CrPC as an abuse of process.'
      };

      const quashResult = await AnalysisService.performAnalysis(testUserId, quashingInput);
      expect(quashResult.generationMode).toBe('typescript_local_fallback');
      const quashArg = quashResult.legalArguments.find(
        (a: any) =>
          a.heading.toLowerCase().includes('civil') ||
          a.heading.toLowerCase().includes('quash') ||
          a.legalProposition.toLowerCase().includes('recovery')
      );
      expect(quashArg).toBeDefined();
      expect(quashArg!.suggestedSubmission).toContain('Bhajan Lal');
    } finally {
      (mlClient as any).baseUrl = originalClient;
    }
  });
});
