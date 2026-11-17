import React from 'react';
import { LegalIssue } from '../../types';

export const LegalIssueCard: React.FC<{ issues: LegalIssue[] }> = ({ issues }) => {
  if (!issues || issues.length === 0) {
    return (
      <div className="bg-ivory-50 border border-ivory-300 rounded p-6 text-xs text-charcoal-600 text-center font-sans">
        No domain-specific question template triggered. Review under general constitutional, civil, and procedural law.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {issues.map((item, idx) => (
        <div
          key={idx}
          className="bg-white border border-gold-500/35 rounded p-5 shadow-sm parchment-card space-y-3"
        >
          <div className="flex items-start gap-2.5">
            <span className="w-6 h-6 rounded bg-navy-950 text-gold-400 text-xs font-serif font-bold flex items-center justify-center shrink-0 mt-0.5">
              {idx + 1}
            </span>
            <h4 className="text-sm font-serif font-bold text-navy-900 leading-snug">
              Question of Law: {item.issue}
            </h4>
          </div>

          <div className="flex items-start gap-2 flex-wrap text-xs">
            <span className="font-serif font-bold text-charcoal-600">Applicable Provisions:</span>
            <span className="font-sans font-semibold text-navy-900 bg-ivory-100 px-2.5 py-0.5 rounded border border-gold-500/30">
              {item.statutoryProvision}
            </span>
          </div>

          {item.relevantFacts && (
            <p className="text-xs text-charcoal-700 leading-relaxed bg-ivory-50 p-3 rounded border border-ivory-200">
              <strong className="font-serif text-navy-900">Relevant Facts: </strong>
              {item.relevantFacts}
            </p>
          )}

          <p className="text-xs text-charcoal-700 leading-relaxed">
            {item.whyIssueMatters || item.description}
          </p>

          {item.supportingAuthorities && item.supportingAuthorities.length > 0 && (
            <div className="text-xs space-y-1">
              <span className="font-serif font-bold text-burgundy-900 block">
                Relevant Supreme Court / Statutory Authorities:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {item.supportingAuthorities.map((auth, aIdx) => (
                  <span
                    key={aIdx}
                    className="bg-white border border-gold-400 text-navy-950 px-2.5 py-0.5 rounded text-[11px] font-medium"
                  >
                    {auth}
                  </span>
                ))}
              </div>
            </div>
          )}

          {item.informationStillRequired && (
            <div className="text-[11.5px] bg-gold-50/70 border border-gold-400 rounded p-2.5 text-charcoal-800">
              <strong className="font-serif text-burgundy-900">Verification Needed: </strong>
              {item.informationStillRequired}
            </div>
          )}

          {item.matchedKeywords && item.matchedKeywords.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-charcoal-500 font-sans pt-1">
              <span className="font-semibold text-charcoal-600 font-serif">Matched Terms:</span>
              {item.matchedKeywords.map((kw, i) => (
                <span
                  key={i}
                  className="bg-ivory-100 text-navy-950 border border-ivory-300 px-1.5 py-0.5 rounded font-mono text-[10.5px]"
                >
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
