import React from 'react';
import { ICaseUnderstanding } from '../../types';
import {
  Users,
  Clock,
  AlertTriangle,
  FileSearch,
  Scale,
  CheckCircle2,
  HelpCircle,
  ClipboardList
} from 'lucide-react';

export const CaseFactsSynthesisView: React.FC<{ understanding?: ICaseUnderstanding }> = ({
  understanding
}) => {
  if (!understanding) return null;

  const {
    parties,
    chronology,
    factClassification,
    disputedActions,
    allegedViolations,
    missingInformation,
    evidenceAudit,
    proceduralPosture,
    proceduralQuestions
  } = understanding;

  const badgeForStatus = (status: string) => {
    if (status === 'User-provided fact') {
      return 'bg-navy-50 text-navy-900 border-navy-200';
    }
    if (status === 'Party allegation') {
      return 'bg-burgundy-50 text-burgundy-900 border-burgundy-200';
    }
    return 'bg-ivory-200 text-charcoal-700 border-gold-400';
  };

  return (
    <div className="space-y-6">
      {/* 1. Litigants */}
      <div className="parchment-card rounded p-5 space-y-3">
        <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2 border-b border-ivory-200 pb-2">
          <Users className="w-4 h-4 text-gold-600" />
          <span>Parties Identified from Supplied Record</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="bg-ivory-50 p-3.5 rounded border border-ivory-300">
            <span className="font-serif font-bold text-navy-900 block mb-1.5">
              Petitioner / Appellant / Applicant
            </span>
            <div className="flex flex-wrap gap-1.5">
              {(parties?.petitioners || ['Not specified.']).map((p, i) => (
                <span
                  key={i}
                  className={`px-2.5 py-1 rounded border font-medium ${
                    p === 'Not specified.'
                      ? 'bg-ivory-100 text-charcoal-500 border-ivory-300 italic'
                      : 'bg-white text-navy-950 border-gold-500/40'
                  }`}
                >
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div className="bg-ivory-50 p-3.5 rounded border border-ivory-300">
            <span className="font-serif font-bold text-navy-900 block mb-1.5">
              Respondent / Prosecution / Opposite Party
            </span>
            <div className="flex flex-wrap gap-1.5">
              {(parties?.respondents || ['Not specified.']).map((r, i) => (
                <span
                  key={i}
                  className={`px-2.5 py-1 rounded border font-medium ${
                    r === 'Not specified.'
                      ? 'bg-ivory-100 text-charcoal-500 border-ivory-300 italic'
                      : 'bg-white text-charcoal-800 border-gold-500/40'
                  }`}
                >
                  {r}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Fact vs Allegation vs Inference Separation */}
      {factClassification && (
        <div className="parchment-card rounded p-5 space-y-4">
          <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2 border-b border-ivory-200 pb-2">
            <Scale className="w-4 h-4 text-gold-600" />
            <span>Strict Classification of Facts, Allegations &amp; Record Gaps</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="bg-ivory-50 border border-ivory-300 rounded p-4 space-y-2">
              <h4 className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-navy-700" />
                <span>User-Provided Facts</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {factClassification.userProvidedFacts?.length ? (
                  factClassification.userProvidedFacts.map((item, idx) => <li key={idx}>{item}</li>)
                ) : (
                  <li className="italic text-charcoal-500">No dated objective events extracted yet.</li>
                )}
              </ul>
            </div>

            <div className="bg-burgundy-50/40 border border-burgundy-200 rounded p-4 space-y-2">
              <h4 className="font-serif font-bold text-burgundy-900 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-burgundy-800" />
                <span>Party Allegations (Unproved)</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {factClassification.partyAllegations?.length ? (
                  factClassification.partyAllegations.map((item, idx) => <li key={idx}>{item}</li>)
                ) : (
                  <li className="italic text-charcoal-500">None separately isolated.</li>
                )}
              </ul>
            </div>

            <div className="bg-white border border-gold-500/30 rounded p-4 space-y-2">
              <h4 className="font-serif font-bold text-navy-900 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-gold-700" />
                <span>Reasonable Legal Inferences (Non-Conclusive)</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
                {factClassification.reasonableInferences?.length ? (
                  factClassification.reasonableInferences.map((item, idx) => <li key={idx}>{item}</li>)
                ) : (
                  <li className="italic text-charcoal-500">Subject to record documents.</li>
                )}
              </ul>
            </div>

            <div className="bg-gold-50/60 border border-gold-400 rounded p-4 space-y-2">
              <h4 className="font-serif font-bold text-charcoal-900 flex items-center gap-1.5">
                <FileSearch className="w-3.5 h-3.5 text-burgundy-900" />
                <span>Facts Requiring Verification / Missing Data</span>
              </h4>
              <ul className="space-y-1.5 list-disc pl-4 text-charcoal-800 leading-relaxed">
                {(factClassification.factsRequiringVerification?.length
                  ? factClassification.factsRequiringVerification
                  : missingInformation
                ).map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 3. Chronology of Dates & Events */}
      {chronology && chronology.length > 0 && (
        <div className="parchment-card rounded p-5 space-y-3">
          <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2 border-b border-ivory-200 pb-2">
            <Clock className="w-4 h-4 text-gold-600" />
            <span>Chronological Synopsis</span>
          </h3>
          <div className="space-y-2.5">
            {chronology.map((ev, i) => (
              <div
                key={i}
                className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 bg-ivory-50 p-3.5 rounded border border-ivory-300 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-bold text-navy-900 bg-white px-2 py-0.5 rounded border border-gold-500/40">
                      {ev.date}
                    </span>
                    <span
                      className={`text-[10.5px] font-semibold px-2 py-0.5 rounded border ${badgeForStatus(
                        ev.verificationStatus
                      )}`}
                    >
                      {ev.verificationStatus}
                    </span>
                  </div>
                  <p className="font-semibold text-charcoal-900 pt-1">{ev.event}</p>
                  {ev.sourceExcerpt && (
                    <p className="text-charcoal-600 italic leading-relaxed">“{ev.sourceExcerpt}”</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Procedural Posture & Available Remedies */}
      {proceduralPosture && (
        <div className="parchment-card rounded p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-2">
            <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-gold-600" />
              <span>Procedural Posture &amp; Maintainable Remedies</span>
            </h3>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">
              {proceduralPosture.detectedPosture}
            </span>
          </div>

          <p className="text-xs text-charcoal-700 bg-ivory-50 p-3 rounded border border-ivory-200 leading-relaxed">
            {proceduralPosture.remedyNote}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {proceduralPosture.availableRemedies?.map((rem, idx) => (
              <div key={idx} className="bg-white border border-gold-500/30 rounded p-4 space-y-1.5 text-xs">
                <h4 className="font-serif font-bold text-burgundy-900">{rem.remedy}</h4>
                <p className="font-mono text-[11px] text-navy-900 font-semibold">{rem.statutoryBasis}</p>
                <p className="text-charcoal-700 leading-relaxed">
                  <strong className="font-serif text-navy-900">When applicable: </strong>
                  {rem.whenApplicable}
                </p>
                <p className="text-[11px] text-charcoal-600 bg-ivory-50 p-2 rounded border border-ivory-200">
                  <strong className="text-burgundy-900">Counsel check: </strong>
                  {rem.cautionNote}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Disputed Actions, Alleged Violations & Evidence Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
        <div className="parchment-card rounded p-5 space-y-2.5">
          <h4 className="font-serif font-bold text-navy-900 uppercase tracking-wide border-b border-ivory-200 pb-2">
            Disputed Actions &amp; Alleged Violations
          </h4>
          {disputedActions?.length > 0 && (
            <ul className="space-y-1 list-disc pl-4 text-charcoal-700">
              {disputedActions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          )}
          {allegedViolations?.length > 0 && (
            <ul className="space-y-1 list-disc pl-4 text-burgundy-900 pt-1">
              {allegedViolations.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="parchment-card rounded p-5 space-y-2.5">
          <h4 className="font-serif font-bold text-navy-900 uppercase tracking-wide border-b border-ivory-200 pb-2">
            Procedural Questions for Record Review
          </h4>
          <ul className="space-y-1.5 list-disc pl-4 text-charcoal-700 leading-relaxed">
            {(proceduralQuestions || []).map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* 6. Evidence Audit Table */}
      {evidenceAudit && evidenceAudit.length > 0 && (
        <div className="parchment-card rounded p-5 space-y-3">
          <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide flex items-center gap-2 border-b border-ivory-200 pb-2">
            <FileSearch className="w-4 h-4 text-gold-600" />
            <span>Missing Documents &amp; Evidentiary Verification Checklist</span>
          </h3>
          <div className="space-y-2.5">
            {evidenceAudit.map((doc, idx) => (
              <div
                key={idx}
                className="bg-ivory-50 border border-ivory-300 rounded p-3.5 text-xs flex flex-col sm:flex-row sm:items-start justify-between gap-2"
              >
                <div className="space-y-1">
                  <p className="font-serif font-bold text-navy-900">{doc.documentName}</p>
                  <p className="text-charcoal-700">{doc.purpose}</p>
                  <p className="text-[11px] text-charcoal-500">{doc.relevanceNote}</p>
                </div>
                <span className="shrink-0 self-start text-[10.5px] font-semibold px-2.5 py-1 rounded bg-gold-100 text-gold-900 border border-gold-400">
                  {doc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
