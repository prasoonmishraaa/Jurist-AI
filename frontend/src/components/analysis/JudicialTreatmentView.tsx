import React from 'react';
import { IJudicialTreatmentAssessment, QualitativeResearchMeta } from '../../types';
import {
  Scale,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Info,
  ShieldAlert,
  Database,
  Lock,
  Cpu,
  BarChart2,
  Sparkles
} from 'lucide-react';

interface JudicialTreatmentViewProps {
  assessment?: IJudicialTreatmentAssessment;
  meta?: QualitativeResearchMeta;
}

const formatClassLabel = (label: string): string => {
  const map: Record<string, string> = {
    appeal_allowed: 'Appeal Allowed',
    appeal_dismissed: 'Appeal Dismissed',
    petition_allowed: 'Petition Allowed',
    petition_dismissed: 'Petition Dismissed',
    respondent: 'Respondent',
    petitioner: 'Petitioner',
    accused: 'Accused',
    state_prosecution: 'State / Prosecution',
    domain_abstained: 'Abstained (Domain Limitation)',
    domain_limited: 'Domain Limited'
  };
  return map[label] || label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

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

export const JudicialTreatmentView: React.FC<JudicialTreatmentViewProps> = ({ assessment, meta }) => {
  if (!assessment && !meta) return null;

  // Exact dataset and model readiness numbers
  const APPROVED_ANNOTATIONS = 46;
  const MINIMUM_TRAINING_THRESHOLD = 30;
  const PROGRESS_PERCENT = Math.min(100, Math.round((APPROVED_ANNOTATIONS / MINIMUM_TRAINING_THRESHOLD) * 100));

  const hasDualModels = Boolean(meta?.modelA && meta?.modelB);
  const disp = meta?.predictedDisposition || meta?.disposition || meta?.modelA?.prediction;
  const party = meta?.predictedSuccessfulParty || meta?.successfulParty || meta?.modelB?.prediction;
  const isPotentiallyInconsistent = checkPotentialInconsistency(disp, party);

  return (
    <div className="space-y-6">
      {/* 1. Dual-Model Experimental Outcome Prediction or Qualitative Panel */}
      {hasDualModels && meta?.modelA && meta?.modelB ? (
        <div className="parchment-card rounded p-6 space-y-5 border-l-4 border-l-gold-600 bg-gradient-to-br from-ivory-50 via-white to-ivory-100">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-300 pb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 font-serif font-bold text-xs px-2.5 py-0.5 rounded bg-navy-950 text-gold-300 border border-gold-500/40 shadow-sm">
                  <Sparkles className="w-3 h-3 text-gold-400" />
                  <span>Experimental Outcome Prediction</span>
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded bg-gold-100 text-gold-900 border border-gold-300">
                  <Cpu className="w-3 h-3 text-gold-700" />
                  <span>Feature 4.26 Presentation Prototype</span>
                </span>
              </div>
              <h3 className="text-base font-serif font-bold text-navy-900">
                Judicial Outcome &amp; Prevailing Party Estimation
              </h3>
            </div>
            <div className="flex items-center gap-2 self-start">
              <span className="text-[11px] font-mono font-medium px-2.5 py-1 rounded bg-green-100 text-green-800 border border-green-300 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-green-700" />
                <span>Dataset Threshold Satisfied (46/30)</span>
              </span>
            </div>
          </div>

          {/* 1. Independent Dual-Model Inference Advisory */}
          <div className="text-[11.5px] text-navy-950 bg-navy-50/80 border border-navy-200/90 rounded p-3.5 flex items-start gap-2.5 leading-relaxed">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-navy-700" />
            <div className="space-y-0.5">
              <span className="font-semibold block text-navy-950">Independent Dual-Model Inference:</span>
              <p className="text-charcoal-700">
                Model A predicts judicial disposition, while Model B estimates the successful party. These are independently trained classifiers and do not condition their predictions on each other. Their outputs may disagree and should be interpreted separately, not as a combined judicial ruling.
              </p>
            </div>
          </div>

          {/* 2. Neutral Inconsistency Warning if Divergent */}
          {isPotentiallyInconsistent && (
            <div className="text-[11.5px] text-amber-950 bg-amber-50 border border-amber-300 rounded p-3.5 flex items-start gap-2.5 leading-relaxed shadow-sm">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
              <div className="space-y-0.5">
                <span className="font-semibold block text-amber-950">Divergent Estimation Notice:</span>
                <p className="text-amber-900">
                  The predicted disposition and prevailing-party category may not describe a logically consistent outcome for this proceeding. Review the case facts and legal context.
                </p>
              </div>
            </div>
          )}

          {/* Model A and Model B Dual Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Model A Card */}
            <div className="bg-white rounded p-4 border border-ivory-300 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-ivory-200 pb-2">
                <div>
                  <span className="text-[10.5px] uppercase tracking-wider font-mono font-bold text-charcoal-500 block">
                    MODEL A &bull; DISPOSITION
                  </span>
                  <span className="font-serif font-bold text-sm text-navy-900">Judicial Disposition</span>
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-navy-50 text-navy-800 border border-navy-200">
                  Macro-F1: {meta.modelA.macroF1?.toFixed(3) ?? '0.256'} (N={meta.modelA.sampleSize ?? 43})
                </span>
              </div>

              <div className="bg-ivory-50 rounded p-3 border border-ivory-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-charcoal-500 block">Estimated Ruling</span>
                  <span className="text-base font-serif font-bold text-navy-950">
                    {formatClassLabel(meta.predictedDisposition || meta.modelA.prediction)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-charcoal-500 block">Uncalibrated Score</span>
                  <span className="text-sm font-mono font-bold text-gold-800">
                    {Math.round((meta.modelA.confidenceScore || 0) * 100)}%
                  </span>
                </div>
              </div>

              {/* Score distribution breakdown */}
              {meta.modelA.uncalibratedScores && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10.5px] font-sans font-semibold text-charcoal-600 block">
                    Precedent Correlation by Disposition Class:
                  </span>
                  {Object.entries(meta.modelA.uncalibratedScores).map(([cls, score]) => {
                    const isWinner = cls === meta.modelA?.prediction;
                    const pct = Math.round(score * 100);
                    return (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span className={isWinner ? 'font-bold text-navy-950' : 'text-charcoal-600'}>
                            {formatClassLabel(cls)}
                          </span>
                          <span className={isWinner ? 'font-bold text-navy-950' : 'text-charcoal-600'}>
                            {pct}%
                          </span>
                        </div>
                        <div className="w-full bg-ivory-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full transition-all ${
                              isWinner ? 'bg-navy-900' : 'bg-gold-500/60'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Model B Card */}
            <div className="bg-white rounded p-4 border border-ivory-300 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-ivory-200 pb-2">
                <div>
                  <span className="text-[10.5px] uppercase tracking-wider font-mono font-bold text-charcoal-500 block">
                    MODEL B &bull; PREVAILING PARTY
                  </span>
                  <span className="font-serif font-bold text-sm text-navy-900">Successful Party</span>
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-green-50 text-green-800 border border-green-200">
                  Macro-F1: {meta.modelB.macroF1?.toFixed(3) ?? '0.366'} (N={meta.modelB.sampleSize ?? 37})
                </span>
              </div>

              <div className="bg-ivory-50 rounded p-3 border border-ivory-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-charcoal-500 block">Estimated Prevailing Side</span>
                  <span className="text-base font-serif font-bold text-navy-950 flex items-center gap-1.5">
                    {meta.modelB.abstained && <AlertTriangle className="w-4 h-4 text-amber-600 inline shrink-0" />}
                    {formatClassLabel(meta.predictedSuccessfulParty || meta.modelB.prediction)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-charcoal-500 block">Uncalibrated Score</span>
                  <span className="text-sm font-mono font-bold text-green-800">
                    {meta.modelB.abstained ? 'N/A' : `${Math.round((meta.modelB.confidenceScore || 0) * 100)}%`}
                  </span>
                </div>
              </div>

              {/* Domain limitation alert if applicable */}
              {meta.modelB.domainLimitation && (
                <div className="text-[11px] text-amber-900 bg-amber-50/90 border border-amber-200 rounded p-2.5 flex items-start gap-1.5 leading-relaxed">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-700" />
                  <span>{meta.modelB.domainLimitation}</span>
                </div>
              )}

              {/* Score distribution breakdown */}
              {meta.modelB.uncalibratedScores && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10.5px] font-sans font-semibold text-charcoal-600 block">
                    Precedent Correlation by Party Class:
                  </span>
                  {Object.entries(meta.modelB.uncalibratedScores).map(([cls, score]) => {
                    const isWinner = cls === meta.modelB?.prediction;
                    const pct = Math.round(score * 100);
                    return (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span className={isWinner ? 'font-bold text-navy-950' : 'text-charcoal-600'}>
                            {formatClassLabel(cls)}
                          </span>
                          <span className={isWinner ? 'font-bold text-navy-950' : 'text-charcoal-600'}>
                            {pct}%
                          </span>
                        </div>
                        <div className="w-full bg-ivory-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full transition-all ${
                              isWinner ? 'bg-green-800' : 'bg-charcoal-300'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Rationale and Pre-decision Safeguard Note */}
          <div className="bg-white p-3.5 rounded border border-ivory-200 text-xs text-charcoal-800 space-y-1">
            <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
              <BarChart2 className="w-3.5 h-3.5 text-gold-600" />
              <span>Model Rationale:</span>
            </div>
            <p className="leading-relaxed">{meta.rationale}</p>
          </div>

          {/* Explicit Research Disclaimers */}
          <div className="text-[11.5px] text-burgundy-900 bg-burgundy-50/70 border border-burgundy-200 rounded p-3 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-burgundy-900" />
            <div className="space-y-1 leading-relaxed">
              <p className="font-semibold">
                Presentation Research Disclaimer:
              </p>
              <p>
                {meta.disclaimer ||
                  'These experimental models are trained on 46 human-verified Indian legal judgments with target leakage sanitization applied to pre-decision text. Uncalibrated scores represent historical precedent vocabulary correlations rather than empirical win probabilities or legal advice.'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* Qualitative Research Mode Fallback */
        <div className="parchment-card rounded p-6 space-y-4 border-l-4 border-l-navy-950">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-serif font-bold text-xs px-2.5 py-0.5 rounded bg-navy-950 text-gold-300 border border-gold-500/30">
                  Qualitative Research Mode
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-200">
                  <Lock className="w-3 h-3 text-burgundy-700" />
                  <span>Statistical Prediction Guarded</span>
                </span>
              </div>
              <h3 className="text-base font-serif font-bold text-navy-900">
                Outcome Analysis &amp; Judicial Treatment Assessment
              </h3>
            </div>
            <span className="text-[11px] font-mono font-medium px-2.5 py-1 rounded bg-ivory-100 text-charcoal-700 border border-ivory-300 self-start">
              Rule 4.10 Gate: Active
            </span>
          </div>

          {/* Training Readiness Progress Box */}
          <div className="bg-ivory-50 rounded border border-ivory-300 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <span className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-gold-700" />
                <span>Verified Dataset Gate ({APPROVED_ANNOTATIONS} / {MINIMUM_TRAINING_THRESHOLD} Verified Precedents)</span>
              </span>
              <span className="font-mono text-charcoal-600 font-semibold">
                {APPROVED_ANNOTATIONS} / {MINIMUM_TRAINING_THRESHOLD} Verified ({PROGRESS_PERCENT}%)
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-ivory-200 rounded-full h-2.5 overflow-hidden border border-ivory-300">
              <div
                className="bg-gold-600 h-2.5 rounded-full transition-all"
                style={{ width: `${PROGRESS_PERCENT}%` }}
              />
            </div>

            <p className="text-[11.5px] text-charcoal-700 leading-relaxed font-sans">
              <strong>Data Integrity Safeguard:</strong> The verified outcome dataset currently has <strong>{APPROVED_ANNOTATIONS} human-approved annotations</strong> (surpassing the {MINIMUM_TRAINING_THRESHOLD}-sample minimum training threshold). Experimental statistical models are evaluated under 5-Fold Cross-Validation, while doctrinal legal analysis remains prioritized for court preparation.
            </p>
          </div>

          {/* Scope Note */}
          <div className="text-xs text-charcoal-800 leading-relaxed bg-white p-3.5 rounded border border-ivory-200">
            <strong className="font-serif text-navy-900 block mb-1">Doctrinal Research Scope:</strong>
            {assessment?.researchScopeNote || meta?.rationale || 'Analysis focuses on established legal standards, applicable statutory provisions, and precedential ratio decidendi rather than statistical speculation.'}
          </div>

          <div className="text-[11.5px] text-burgundy-900 bg-burgundy-50/60 border border-burgundy-200 rounded p-3 flex items-start gap-2">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-burgundy-900" />
            <span>
              {meta?.disclaimer ||
                'Legal outcomes in Indian courts turn upon primary evidence, credible testimony, statutory limitations, and judicial discretion under Article 141/142. The analysis provided below details settled judicial principles and supporting authorities to guide counsel research.'}
            </span>
          </div>
        </div>
      )}

      {assessment && (
        <>
          {/* Settled Historical Legal Principles */}
          {assessment.historicalLegalPrinciples?.length > 0 && (
            <div className="parchment-card rounded p-5 space-y-3 text-xs">
              <h4 className="font-serif font-bold text-navy-900 uppercase tracking-wide border-b border-ivory-200 pb-2 flex items-center gap-2">
                <Scale className="w-4 h-4 text-gold-600" />
                <span>Settled Judicial Principles Implicated by Facts</span>
              </h4>
              <ul className="space-y-2 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {assessment.historicalLegalPrinciples.map((p, idx) => (
                  <li key={idx} className="pl-1">
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Supporting vs Distinguishing/Adverse Authorities */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            <div className="parchment-card rounded p-5 space-y-3">
              <h4 className="font-serif font-bold text-navy-900 flex items-center gap-1.5 border-b border-ivory-200 pb-2">
                <CheckCircle2 className="w-4 h-4 text-navy-800" />
                <span>Supporting Judicial Authorities</span>
              </h4>
              {assessment.supportingAuthorities?.length > 0 ? (
                <div className="space-y-2.5">
                  {assessment.supportingAuthorities.map((item, idx) => (
                    <div key={idx} className="bg-ivory-50 p-3 rounded border border-ivory-300 space-y-1">
                      <p className="font-serif font-bold text-navy-900">{item.caseTitle}</p>
                      <p className="font-mono text-[11px] text-burgundy-900">{item.citation}</p>
                      <p className="text-charcoal-700 leading-relaxed pt-0.5">{item.proposition}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-charcoal-500 italic">No directly supportive authorities isolated in current corpus.</p>
              )}
            </div>

            <div className="parchment-card rounded p-5 space-y-3">
              <h4 className="font-serif font-bold text-burgundy-900 flex items-center gap-1.5 border-b border-ivory-200 pb-2">
                <AlertTriangle className="w-4 h-4 text-burgundy-900" />
                <span>Distinguishing &amp; Potentially Adverse Authorities</span>
              </h4>
              {assessment.distinguishingOrAdverseAuthorities?.length > 0 ? (
                <div className="space-y-2.5">
                  {assessment.distinguishingOrAdverseAuthorities.map((item, idx) => (
                    <div key={idx} className="bg-burgundy-50/40 p-3 rounded border border-burgundy-200 space-y-1">
                      <p className="font-serif font-bold text-navy-900">{item.caseTitle}</p>
                      <p className="font-mono text-[11px] text-burgundy-900">{item.citation}</p>
                      <p className="text-charcoal-700 leading-relaxed pt-0.5">{item.distinctionNote}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-charcoal-500 italic">
                  Counsel should still verify factual exceptions in special enactments and counter-affidavits.
                </p>
              )}
            </div>
          </div>

          {/* Factual Determinants & Scope Limitations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            <div className="parchment-card rounded p-5 space-y-2.5">
              <h4 className="font-serif font-bold text-navy-900 flex items-center gap-1.5 border-b border-ivory-200 pb-2">
                <HelpCircle className="w-4 h-4 text-gold-600" />
                <span>Factual Determinants on Which Relief Turns</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {(assessment.keyFactualDeterminants || []).map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>

            <div className="parchment-card rounded p-5 space-y-2.5 bg-gold-50/30">
              <h4 className="font-serif font-bold text-burgundy-900 border-b border-ivory-200 pb-2 flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-burgundy-800" />
                <span>Research Scope Limitations</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {(assessment.researchLimitations || []).map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
