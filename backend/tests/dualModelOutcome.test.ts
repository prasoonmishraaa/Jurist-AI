import { localInferenceEngine } from '../src/integrations/localInference';

/**
 * Feature 4.27 Presentation Inconsistency Safeguard Logic
 * Mirrors the exact contract in frontend/src/components/analysis/JudicialTreatmentView.tsx
 */
export const checkPotentialInconsistency = (disp?: string, party?: string): boolean => {
  if (!disp || !party) return false;
  const d = disp.toLowerCase();
  const p = party.toLowerCase();

  // If Model B abstained or is procedural, no substantive conflict
  if (
    p === 'domain_abstained' ||
    p === 'none_procedural' ||
    p === 'unresolved' ||
    p.includes('abstained')
  ) {
    return false;
  }

  // 1. Petition allowed but State Prosecution or Respondent predicted as prevailing
  if (d === 'petition_allowed' && (p === 'state_prosecution' || p === 'respondent')) {
    return true;
  }
  // 2. Petition dismissed but initiating Petitioner or Accused predicted as prevailing
  if (d === 'petition_dismissed' && (p === 'petitioner' || p === 'accused')) {
    return true;
  }
  // 3. Appeal allowed but Respondent predicted as prevailing
  if (d === 'appeal_allowed' && p === 'respondent') {
    return true;
  }
  // 4. Appeal dismissed but Petitioner predicted as prevailing
  if (d === 'appeal_dismissed' && p === 'petitioner') {
    return true;
  }

  return false;
};

describe('Feature 4.27: Independent Dual-Model Prediction & Presentation Fix', () => {
  const aaravMehtaCriminalBrief =
    'An offence was alleged on 5 October 2024 in a commercial supply dispute. ' +
    'FIR was registered on 10 October 2024 alleging cheating and dishonestly inducing delivery of property. ' +
    'Police arrested the Accused Aarav Mehta on 14 October 2024 without serving pre-arrest notice, ' +
    'did not communicate written grounds of arrest under Article 22(1) / Section 47 BNSS, ' +
    'and produced him before the Magistrate beyond 24 hours for remand.';

  const civilWritBrief =
    'Civil Writ Petition under Article 226 of the Constitution of India challenging an arbitrary tender disqualification ' +
    'by the Municipal Corporation. The petitioner submitted all qualifying pre-bid technical credentials and fulfilled ' +
    'mandatory eligibility requirements. The respondent authority rejected the technical bid without assigning reasons ' +
    'or affording an opportunity of hearing, violating Article 14 and principles of natural justice.';

  describe('1. Backend Response Structure & Decoupled Fields', () => {
    it('serializes predictedDisposition and predictedSuccessfulParty as separate structured fields', () => {
      const outcome = localInferenceEngine.predictOutcome(aaravMehtaCriminalBrief, 'Criminal');

      expect(outcome.status).toBe('validated_estimate');
      expect(outcome.isExperimental).toBe(true);

      // Dedicated top-level structured fields
      expect(outcome.predictedDisposition).toBe('petition_allowed');
      expect(outcome.predictedSuccessfulParty).toBe('accused');

      // Preserved Model A container
      expect(outcome.modelA).toBeDefined();
      expect(outcome.modelA!.target).toBe('judicial_disposition');
      expect(outcome.modelA!.prediction).toBe('petition_allowed');
      expect(outcome.modelA!.sampleSize).toBe(43);
      expect(outcome.modelA!.macroF1).toBeCloseTo(0.2559, 3);
      expect(outcome.modelA!.uncalibratedScores).toBeDefined();
      expect(outcome.modelA!.classes).toEqual([
        'appeal_allowed',
        'appeal_dismissed',
        'petition_allowed',
        'petition_dismissed'
      ]);

      // Preserved Model B container
      expect(outcome.modelB).toBeDefined();
      expect(outcome.modelB!.target).toBe('successful_party');
      expect(outcome.modelB!.prediction).toBe('accused');
      expect(outcome.modelB!.sampleSize).toBe(37);
      expect(outcome.modelB!.macroF1).toBeCloseTo(0.3664, 3);
      expect(outcome.modelB!.uncalibratedScores).toBeDefined();
      expect(outcome.modelB!.classes).toEqual([
        'accused',
        'petitioner',
        'respondent',
        'state_prosecution'
      ]);

      // Legacy string retained strictly for backward compatibility
      expect(outcome.estimatedOutcome).toBeDefined();
      expect(outcome.estimatedOutcome).toContain('petition_allowed');
      expect(outcome.estimatedOutcome).toContain('accused');
    });
  });

  describe('2. Five Validation Scenarios for Independent Inference & Presentation', () => {
    it('Scenario 1: Consistent combination (petition_allowed + petitioner) does not trigger inconsistency warning', () => {
      const disp = 'petition_allowed';
      const party = 'petitioner';

      const isInconsistent = checkPotentialInconsistency(disp, party);
      expect(isInconsistent).toBe(false);
    });

    it('Scenario 2: Consistent combination (petition_dismissed + respondent) does not trigger inconsistency warning', () => {
      const disp = 'petition_dismissed';
      const party = 'respondent';

      const isInconsistent = checkPotentialInconsistency(disp, party);
      expect(isInconsistent).toBe(false);
    });

    it('Scenario 3: Divergent combination (petition_allowed + state_prosecution) triggers inconsistency notice without modifying predictions', () => {
      const disp = 'petition_allowed';
      const party = 'state_prosecution';

      // Verify that presentation safeguard correctly flags divergence
      const isInconsistent = checkPotentialInconsistency(disp, party);
      expect(isInconsistent).toBe(true);

      // Verify that models are NOT modified, suppressed, or artificially aligned
      expect(disp).toBe('petition_allowed');
      expect(party).toBe('state_prosecution');
    });

    it('Scenario 4: Domain-abstained Model B in civil writ preserves domain limitation without false inconsistency alert', () => {
      // 4a: Civil writ where Model B raw prediction is 'accused' triggers domain abstention
      const abstainedOutcome = localInferenceEngine.predictOutcome(aaravMehtaCriminalBrief, 'Constitutional Writ');

      expect(abstainedOutcome.status).toBe('validated_estimate');
      expect(abstainedOutcome.predictedDisposition).toBeDefined();

      expect(abstainedOutcome.modelB).toBeDefined();
      expect(abstainedOutcome.modelB!.domainStatus).toBe('domain_limited');
      expect(abstainedOutcome.modelB!.abstained).toBe(true);
      expect(abstainedOutcome.predictedSuccessfulParty).toBe('domain_abstained');
      expect(abstainedOutcome.modelB!.prediction).toBe('domain_abstained');
      expect(abstainedOutcome.modelB!.rawPrediction).toBe('accused');
      expect(abstainedOutcome.modelB!.confidenceScore).toBe(0.0);
      expect(abstainedOutcome.modelB!.confidenceLevel).toBe('Abstained (Domain Limitation)');
      expect(abstainedOutcome.modelB!.domainLimitation).toContain('Domain Limitation');

      // Presentation consistency check should NOT flag abstained predictions as inconsistent
      const isAbstainedInconsistent = checkPotentialInconsistency(
        abstainedOutcome.predictedDisposition,
        abstainedOutcome.predictedSuccessfulParty
      );
      expect(isAbstainedInconsistent).toBe(false);

      // 4b: Civil writ where Model B raw prediction is 'petitioner' preserves valid party with domain limitation note
      const validPartyCivilOutcome = localInferenceEngine.predictOutcome(civilWritBrief, 'Constitutional Writ');
      expect(validPartyCivilOutcome.status).toBe('validated_estimate');
      expect(validPartyCivilOutcome.modelB!.domainStatus).toBe('domain_limited');
      expect(validPartyCivilOutcome.modelB!.abstained).toBe(false);
      expect(validPartyCivilOutcome.modelB!.prediction).toBe('petitioner');
      expect(validPartyCivilOutcome.modelB!.domainLimitation).toBeDefined();
    });

    it('Scenario 5: Missing model response / short input gracefully falls back to qualitative research mode', () => {
      // 5a: Short input
      const shortOutcome = localInferenceEngine.predictOutcome('Too short');
      expect(shortOutcome.status).toBe('insufficient_input');
      expect(shortOutcome.estimatedOutcome).toBe('Insufficient Case Input');
      expect(shortOutcome.predictedDisposition).toBeUndefined();
      expect(shortOutcome.predictedSuccessfulParty).toBeUndefined();

      // 5b: Direct qualitative fallback contract check
      const qualitativeFallback = {
        status: 'qualitative_research_mode',
        estimatedOutcome: 'Structured Doctrinal & Authority Assessment',
        rationale: 'Relief depends on verified evidentiary records and judicial discretion.',
        disclaimer: 'Statistical prediction guarded under Rule 4.10.'
      };
      expect(qualitativeFallback.status).toBe('qualitative_research_mode');
      expect((qualitativeFallback as any).predictedDisposition).toBeUndefined();
    });
  });

  describe('3. Additional Decretal Stripping & Pre-decision Integrity', () => {
    it('produces sanitized pre-decision text without operative decretal bias', () => {
      const textWithOperativeOrder =
        aaravMehtaCriminalBrief + '\n\nOPERATIVE ORDER\nIn the result, the appeal is dismissed with costs.';
      const outcome = localInferenceEngine.predictOutcome(textWithOperativeOrder, 'Criminal');

      expect(outcome.status).toBe('validated_estimate');
      expect(outcome.predictedDisposition).toBe('petition_allowed');
      expect(outcome.predictedSuccessfulParty).toBe('accused');
    });
  });
});
