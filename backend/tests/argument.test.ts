import { LegalArgumentService } from '../src/services/argumentService';
import { LegislationService } from '../src/services/legislationService';
import { localInferenceEngine } from '../src/integrations/localInference';
import { IMatchedPrecedent } from '../src/models/Analysis';

describe('Date-Aware Indian Legislation & Legal Argument Service', () => {
  it('Test A: post-July 2024 cheating arrest applies BNSS/BNS without hallucinating S. 498A or anticipatory bail', () => {
    const postJuly2024Facts =
      'An offence was alleged on 5 October 2024 in a business vendor payment dispute. FIR was registered on 10 October 2024 alleging cheating and dishonestly inducing delivery of property. Police arrested the accused on 14 October 2024 without prior notice, did not furnish written grounds of arrest, and kept him in police custody beyond 24 hours without Magistrate remand.';

    const law = LegislationService.assessApplicableLegislation(postJuly2024Facts, 'Criminal Law');
    expect(law.regimeStatus).toBe('post_july_2024_new_codes');
    expect(law.substantiveLaw.some(s => s.statute.includes('BNS') || s.provision.includes('318'))).toBe(true);
    expect(law.proceduralLaw.some(s => s.statute.includes('BNSS') || s.provision.includes('47'))).toBe(true);

    const understanding = LegalArgumentService.analyzeCaseFacts(
      postJuly2024Facts,
      'Criminal Law',
      'High Court',
      law
    );

    // Must not invent party names
    expect(understanding.parties.petitioners).toEqual(['Not specified.']);
    expect(understanding.parties.respondents).toEqual(['Not specified.']);

    // Already arrested / in custody -> must NOT suggest anticipatory bail
    expect(understanding.proceduralPosture.custodyStatus).toBe('in_custody_arrested');
    const remedyNames = understanding.proceduralPosture.availableRemedies.map(r => r.remedy.toLowerCase()).join(' ');
    expect(remedyNames).not.toContain('anticipatory bail');
    expect(remedyNames).toMatch(/regular bail|habeas corpus|magistrate/);

    // Precedents should prioritize Vihaan Kumar / Prabir Purkayastha / Mihir Rajesh Shah / Arnesh Kumar / Satender Kumar Antil
    const matchedPrecedents = localInferenceEngine.retrieveSimilarPrecedents(postJuly2024Facts, 6) as IMatchedPrecedent[];
    expect(matchedPrecedents.length).toBeGreaterThan(0);
    matchedPrecedents.forEach(p => {
      expect(p.sourceUrl).not.toContain('main.sci.gov.in');
    });

    const legalArguments = LegalArgumentService.generateLegalArguments(
      postJuly2024Facts,
      'Criminal Law',
      'High Court',
      matchedPrecedents,
      understanding,
      law
    );

    expect(legalArguments.length).toBeGreaterThan(0);
    for (const arg of legalArguments) {
      expect(arg.applicableProvisions.join(' ')).not.toContain('498A');
      expect(arg.legalProposition).not.toContain('498A');
      expect(arg.suggestedSubmission).not.toContain('498A');
      expect(arg.suggestedSubmission).not.toMatch(/anticipatory bail/i);
    }
    const fullTextDump = JSON.stringify(legalArguments);
    expect(fullTextDump).toContain('Article 22');
    expect(legalArguments[0].suggestedSubmission).toContain('DRAFT RESEARCH SUBMISSION');
    expect(legalArguments[0].counterarguments.length).toBeGreaterThan(0);
    expect(legalArguments[0].draftDisclaimer).toBeDefined();
  });

  it('should detect missing transition date when dates are omitted in criminal facts', () => {
    const undatedFacts =
      'Police arrested the accused at midnight without serving any written notice or grounds of arrest following a commercial dispute.';
    const law = LegislationService.assessApplicableLegislation(undatedFacts, 'Criminal Law');
    expect(law.regimeStatus).toBe('uncertain_missing_dates');
    expect(law.missingDates.length).toBeGreaterThan(0);
  });

  it('should apply pre-July 2024 CrPC/IPC regime for 2023 FIR/arrest events', () => {
    const preJuly2024Facts =
      'An FIR was registered on 10 May 2023 under Section 420 IPC and arrest was effected on 12 June 2023 without notice under Section 41A CrPC.';
    const law = LegislationService.assessApplicableLegislation(preJuly2024Facts, 'Criminal Law');
    expect(law.regimeStatus).toBe('pre_july_2024_legacy_codes');
  });
});
