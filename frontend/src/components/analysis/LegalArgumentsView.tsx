import React, { useState, useEffect } from 'react';
import { ILegalArgument } from '../../types';
import {
  Scale,
  Copy,
  Check,
  ExternalLink,
  AlertTriangle,
  ShieldAlert,
  FileText,
  Save,
  RotateCcw,
  CheckCircle2
} from 'lucide-react';

interface LegalArgumentsViewProps {
  argumentsList?: ILegalArgument[];
  editedDrafts?: Record<string, string>;
  onSaveDraft?: (groundId: string, editedText: string) => Promise<void>;
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
}

const EMPTY_DRAFTS: Record<string, string> = {};

export const LegalArgumentsView: React.FC<LegalArgumentsViewProps> = ({
  argumentsList,
  editedDrafts = EMPTY_DRAFTS,
  onSaveDraft,
  citationGrounding,
  generationMode
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [draftTexts, setDraftTexts] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedNoticeId, setSavedNoticeId] = useState<string | null>(null);

  useEffect(() => {
    if (!argumentsList) return;
    setDraftTexts((prev) => {
      let changed = false;
      const next: Record<string, string> = { ...prev };
      for (const arg of argumentsList) {
        const val = editedDrafts[arg.id] ?? arg.suggestedSubmission;
        if (prev[arg.id] !== val) {
          next[arg.id] = val;
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [argumentsList, editedDrafts]);

  if (!argumentsList || argumentsList.length === 0) {
    return (
      <div className="bg-ivory-50 border border-ivory-300 rounded p-6 text-xs text-charcoal-600 text-center">
        No specific statutory arguments generated for this record.
      </div>
    );
  }

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyAll = () => {
    const compiled = argumentsList
      .map(
        (arg) =>
          `${arg.groundNumber.toUpperCase()}: ${arg.heading}\nLegal Question: ${
            arg.legalQuestion || ''
          }\n\n${draftTexts[arg.id] || arg.suggestedSubmission}\n\n----------------------------------------\n`
      )
      .join('\n');
    handleCopy('all-grounds', compiled);
  };

  const handleSave = async (argId: string) => {
    if (!onSaveDraft) return;
    try {
      setSavingId(argId);
      await onSaveDraft(argId, draftTexts[argId] || '');
      setSavedNoticeId(argId);
      setTimeout(() => setSavedNoticeId(null), 2500);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-gold-500/35 rounded p-4 parchment-card">
        <div className="space-y-0.5">
          <h3 className="text-sm font-serif font-bold text-navy-900">
            Structured Legal Grounds, Authority Application &amp; Editable Draft Submissions
          </h3>
          <p className="text-xs text-charcoal-600">
            Draft pleadings below can be edited directly for chamber review and saved to your dossier.
          </p>
        </div>
        <button
          type="button"
          onClick={handleCopyAll}
          className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded text-xs font-semibold bg-navy-900 hover:bg-navy-800 text-gold-300 border border-gold-500/40 shrink-0 transition-colors"
        >
          {copiedId === 'all-grounds' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copiedId === 'all-grounds' ? 'All Drafts Copied' : 'Copy All Draft Grounds'}</span>
        </button>
      </div>

      {/* Citation Grounding & Generation Mode Audit Banner */}
      <div className="bg-ivory-50 border border-gold-500/30 rounded p-4 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gold-500/20 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-navy-900">
              Intelligence Mode:
            </span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-navy-900 text-gold-300 border border-gold-500/30">
              {generationMode === 'gemini_direct'
                ? 'Google Gemini Direct LLM (Structured Input, No RAG)'
                : generationMode === 'openai_direct'
                ? 'OpenAI Direct LLM (Structured Input, No RAG)'
                : generationMode === 'typescript_local_fallback'
                ? 'Deterministic Indian Legal Analysis (Local Fallback)'
                : 'Deterministic Indian Legal Analysis (Offline)'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-charcoal-600 font-medium">Citation Grounding:</span>
            {citationGrounding ? (
              <span
                className={`font-semibold px-2 py-0.5 rounded ${
                  citationGrounding.isFullyGrounded
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-300'
                    : 'bg-amber-50 text-amber-900 border border-amber-300'
                }`}
              >
                {Math.round((citationGrounding.groundingRatio || 0) * 100)}% Verified against Landmark Corpus
                ({citationGrounding.groundedCitationsCount}/{citationGrounding.totalCitationsCited} authorities)
              </span>
            ) : (
              <span className="text-charcoal-600 italic">Precedents linked directly to internal corpus</span>
            )}
          </div>
        </div>

        <div className="flex items-start gap-2 text-[11px] text-charcoal-600">
          <ShieldAlert className="w-3.5 h-3.5 text-gold-600 shrink-0 mt-0.5" />
          <p>
            <strong>Epistemic Separation Notice: </strong>
            Retrieved precedents and statutory citations are verified against actual legal records.
            Suggested pleading formulations and counterarguments are AI-generated assistive research drafts
            requiring mandatory verification and review by qualified counsel before court submission.
            Citation verification confirms authority existence in internal corpus records and does not constitute proof that a legal proposition is judicially correct.
          </p>
        </div>
      </div>

      {/* Individual Legal Grounds */}
      {argumentsList.map((arg) => {
        const currentDraft = draftTexts[arg.id] ?? arg.suggestedSubmission;
        const isEditedFromGenerated = currentDraft !== arg.suggestedSubmission;

        return (
          <div key={arg.id} className="parchment-card rounded overflow-hidden border border-gold-500/40">
            {/* Title Banner */}
            <div className="bg-navy-950 text-white px-5 py-4 border-b border-gold-500/30 space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-serif uppercase tracking-widest text-gold-400 font-semibold">
                  {arg.groundNumber}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] bg-amber-950/80 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40 font-medium">
                    Requires Advocate Review
                  </span>
                  {isEditedFromGenerated && (
                    <span className="text-[10.5px] bg-burgundy-900 text-gold-200 px-2 py-0.5 rounded border border-gold-500/40">
                      Edited by Counsel
                    </span>
                  )}
                </div>
              </div>
              <h4 className="text-base font-serif font-bold text-white leading-snug">{arg.heading}</h4>
              {arg.legalQuestion && (
                <p className="text-xs text-gold-200/90 leading-relaxed">
                  <strong>Legal Question: </strong>
                  {arg.legalQuestion}
                </p>
              )}
            </div>

            <div className="p-5 space-y-5 text-xs">
              {/* Applicable Provisions */}
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="font-serif font-bold text-navy-900 mr-1">Governing Law:</span>
                {arg.applicableProvisions.map((prov, idx) => (
                  <span
                    key={idx}
                    className="bg-ivory-100 text-burgundy-900 font-semibold px-2.5 py-0.5 rounded border border-gold-500/30"
                  >
                    {prov}
                  </span>
                ))}
              </div>

              {/* Proposition & Facts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-ivory-50 p-3.5 rounded border border-ivory-300 space-y-1">
                  <h5 className="font-serif font-bold text-navy-900">1. Legal Proposition</h5>
                  <p className="text-charcoal-700 leading-relaxed">{arg.legalProposition}</p>
                </div>
                <div className="bg-ivory-50 p-3.5 rounded border border-ivory-300 space-y-1">
                  <h5 className="font-serif font-bold text-navy-900">2. Fact Basis in Record</h5>
                  <p className="text-charcoal-700 leading-relaxed">{arg.relevantFacts}</p>
                </div>
              </div>

              {/* Supporting Precedents */}
              <div className="space-y-2.5">
                <h5 className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5 text-gold-600" />
                  <span>3. Binding / Persuasive Judicial Authorities</span>
                </h5>
                <div className="space-y-2.5">
                  {arg.supportingPrecedents.map((prec, pIdx) => (
                    <div key={pIdx} className="bg-white border border-ivory-300 rounded p-3.5 space-y-1.5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <span className="font-serif font-bold text-navy-900">{prec.caseTitle}</span>
                          <span className="ml-2 font-mono text-[11px] text-burgundy-900 font-semibold">
                            {prec.citation}
                          </span>
                        </div>
                        {prec.isCorpusGrounded === false || prec.verificationStatus === 'unverified' ? (
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-300 self-start">
                            <AlertTriangle className="w-3 h-3 text-amber-600" /> Corpus Unverified Citation
                          </span>
                        ) : prec.officialSourceVerified ? (
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200 self-start">
                            <CheckCircle2 className="w-3 h-3" /> Official Verified
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-200 self-start">
                            <AlertTriangle className="w-3 h-3" /> Official source not verified
                          </span>
                        )}
                      </div>

                      {prec.verificationWarning && (
                        <div className="bg-amber-50/90 border border-amber-200 rounded p-2 text-[11px] text-amber-900 flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                          <span>{prec.verificationWarning}</span>
                        </div>
                      )}

                      <p className="text-[11px] text-charcoal-500">{prec.authorityType}</p>
                      <p className="text-charcoal-700 leading-relaxed">
                        <strong>Held / Ratio: </strong>
                        {prec.ratioPrinciple}
                      </p>
                      <p className="text-charcoal-700 leading-relaxed">
                        <strong>Application: </strong>
                        {prec.applicationToFacts}
                      </p>

                      <div className="flex flex-wrap gap-3 pt-1">
                        {prec.officialSourceVerified && prec.officialSourceUrl && (
                          <a
                            href={prec.officialSourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-navy-900 hover:text-burgundy-900 underline"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>{prec.officialSourceLabel || 'Official PDF'}</span>
                          </a>
                        )}
                        {prec.secondaryReferenceUrl && (
                          <a
                            href={prec.secondaryReferenceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-medium text-burgundy-900 hover:text-navy-900 underline"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>{prec.secondaryReferenceLabel || 'Indian Kanoon Index'}</span>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Judicial Reasoning & Distinctions */}
              <div className="bg-ivory-50 border border-ivory-300 rounded p-4 space-y-2">
                <h5 className="font-serif font-bold text-navy-900">
                  4. Ratio Decidendi, Judicial Reasoning &amp; Factual Application
                </h5>
                {arg.ratioDecidendi && (
                  <p className="text-charcoal-800 leading-relaxed">
                    <strong>Ratio Decidendi: </strong>
                    {arg.ratioDecidendi}
                  </p>
                )}
                <p className="text-charcoal-700 leading-relaxed">
                  <strong>Reasoning: </strong>
                  {arg.judicialReasoning}
                </p>
                <p className="text-charcoal-700 leading-relaxed">
                  <strong>Application to Facts: </strong>
                  {arg.applicationToFacts}
                </p>
                {arg.factualDistinctions && (
                  <p className="text-burgundy-900 bg-white p-2.5 rounded border border-gold-400 leading-relaxed">
                    <strong>Factual Distinctions / Scope Limits: </strong>
                    {arg.factualDistinctions}
                  </p>
                )}
              </div>

              {/* Editable Court Submission Draft */}
              <div className="bg-white border border-navy-900/20 rounded p-4 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-2">
                  <div className="space-y-0.5">
                    <h5 className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-burgundy-900" />
                      <span>5. Editable Court Submission Draft</span>
                    </h5>
                    <p className="text-[11px] text-burgundy-900">
                      {arg.draftDisclaimer ||
                        'Draft legal research submissions — subject to verification and review by qualified counsel.'}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {isEditedFromGenerated && (
                      <button
                        type="button"
                        onClick={() =>
                          setDraftTexts((prev) => ({
                            ...prev,
                            [arg.id]: arg.suggestedSubmission
                          }))
                        }
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-ivory-100 hover:bg-ivory-200 text-charcoal-800 border border-ivory-400"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Reset</span>
                      </button>
                    )}

                    {onSaveDraft && (
                      <button
                        type="button"
                        disabled={savingId === arg.id}
                        onClick={() => handleSave(arg.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded text-[11px] font-semibold bg-burgundy-900 hover:bg-burgundy-800 text-gold-200 disabled:opacity-60"
                      >
                        {savedNoticeId === arg.id ? (
                          <>
                            <Check className="w-3 h-3" />
                            <span>Saved</span>
                          </>
                        ) : (
                          <>
                            <Save className="w-3 h-3" />
                            <span>{savingId === arg.id ? 'Saving...' : 'Save Draft'}</span>
                          </>
                        )}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => handleCopy(arg.id, currentDraft)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-navy-900 hover:bg-navy-800 text-gold-300"
                    >
                      {copiedId === arg.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedId === arg.id ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>

                <textarea
                  value={currentDraft}
                  onChange={(e) =>
                    setDraftTexts((prev) => ({
                      ...prev,
                      [arg.id]: e.target.value
                    }))
                  }
                  rows={8}
                  aria-label={`Editable draft submission for ${arg.groundNumber}`}
                  className="w-full p-3.5 rounded bg-ivory-50 border border-ivory-300 font-sans text-xs text-charcoal-900 leading-relaxed focus:outline-none focus:border-navy-900 focus:ring-1 focus:ring-navy-900"
                />
              </div>

              {/* Evidence Required & Weaknesses/Limitations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {arg.evidenceRequired && arg.evidenceRequired.length > 0 && (
                  <div className="bg-ivory-50 border border-ivory-300 rounded p-3.5 space-y-1.5">
                    <h5 className="font-serif font-bold text-navy-900">6. Documentary Evidence Needed</h5>
                    <ul className="space-y-1 list-disc pl-4 text-charcoal-700">
                      {arg.evidenceRequired.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="bg-gold-50/60 border border-gold-400 rounded p-3.5 space-y-1.5">
                  <h5 className="font-serif font-bold text-burgundy-900">
                    7. Weaknesses, Conditions &amp; Verification Limits
                  </h5>
                  {arg.weaknesses && (
                    <p className="text-charcoal-800 leading-relaxed">
                      <strong>Weaknesses: </strong>
                      {arg.weaknesses}
                    </p>
                  )}
                  <p className="text-charcoal-700 leading-relaxed">
                    <strong>Limitations: </strong>
                    {arg.limitations}
                  </p>
                </div>
              </div>

              {/* Opposing Counsel Submissions & Rebuttal Strategy */}
              {arg.counterarguments && arg.counterarguments.length > 0 && (
                <div className="space-y-3 pt-1">
                  <h5 className="font-serif font-bold text-burgundy-900 flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-burgundy-900" />
                    <span>8. Anticipated Opposing Counsel Arguments &amp; Rebuttal Strategy</span>
                  </h5>
                  <div className="space-y-3">
                    {arg.counterarguments.map((c, cIdx) => (
                      <div
                        key={cIdx}
                        className="bg-burgundy-50/40 border border-burgundy-200 rounded p-4 space-y-2"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <span className="font-serif font-bold text-burgundy-900">{c.opposingGround}</span>
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-white text-charcoal-800 border border-gold-400 self-start">
                            Risk Assessment: {c.vulnerabilityAssessment}
                          </span>
                        </div>
                        <p className="text-charcoal-700 leading-relaxed">
                          <strong>Opposing Legal Basis: </strong>
                          {c.opposingLegalBasis}
                        </p>
                        {c.factualBasis && (
                          <p className="text-charcoal-600 leading-relaxed">
                            <strong>Factual Trigger: </strong>
                            {c.factualBasis}
                          </p>
                        )}
                        <p className="text-navy-950 bg-white p-2.5 rounded border border-ivory-300 leading-relaxed">
                          <strong>Prepared Rebuttal Strategy: </strong>
                          {c.rebuttalStrategy}
                        </p>
                        <p className="text-[11px] text-charcoal-600">
                          <strong>Record / Evidence to Establish Rebuttal: </strong>
                          {c.requiredEvidence}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
