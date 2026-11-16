import React from 'react';
import { ExtractedEntities } from '../../types';
import { Book, Landmark, Scale, Users, Bookmark } from 'lucide-react';

export const EntityBadgesView: React.FC<{ entities?: ExtractedEntities }> = ({ entities }) => {
  if (!entities) return null;

  const hasPetitioners = (entities.parties?.petitioners || []).some((p) => p !== 'Not specified.');
  const hasRespondents = (entities.parties?.respondents || []).some((r) => r !== 'Not specified.');

  return (
    <div className="space-y-5">
      {(hasPetitioners || hasRespondents) && (
        <div className="bg-white border border-gold-500/30 rounded p-5 parchment-card space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-gold-600" />
            <span>Named Parties Found in Text</span>
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-sans">
            <div className="bg-ivory-50 p-3 rounded border border-ivory-300">
              <span className="font-serif font-bold text-navy-900 block mb-1">Petitioners / Complainants:</span>
              <div className="flex flex-wrap gap-1.5">
                {entities.parties?.petitioners.map((p, i) => (
                  <span
                    key={i}
                    className="bg-white text-navy-950 border border-gold-500/30 px-2.5 py-1 rounded font-medium"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
            <div className="bg-ivory-50 p-3 rounded border border-ivory-300">
              <span className="font-serif font-bold text-navy-900 block mb-1">Respondents / Opposite Parties:</span>
              <div className="flex flex-wrap gap-1.5">
                {entities.parties?.respondents.map((r, i) => (
                  <span
                    key={i}
                    className="bg-white text-charcoal-800 border border-gold-500/30 px-2.5 py-1 rounded font-medium"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {((entities.statutes && entities.statutes.length > 0) ||
        (entities.sections && entities.sections.length > 0)) && (
        <div className="bg-white border border-gold-500/30 rounded p-5 parchment-card space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 flex items-center gap-1.5">
            <Book className="w-3.5 h-3.5 text-gold-600" />
            <span>Statutes &amp; Legislative Provisions Referenced</span>
          </h4>
          <div className="space-y-3 text-xs">
            {entities.statutes && entities.statutes.length > 0 && (
              <div>
                <span className="font-serif font-bold text-charcoal-600 block mb-1.5">Enactments Mentioned:</span>
                <div className="flex flex-wrap gap-2">
                  {entities.statutes.map((s, i) => (
                    <span
                      key={i}
                      className="bg-ivory-100 text-navy-950 border border-gold-500/30 px-3 py-1 rounded font-medium"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {entities.sections && entities.sections.length > 0 && (
              <div>
                <span className="font-serif font-bold text-charcoal-600 block mb-1.5">Specific Sections / Articles:</span>
                <div className="flex flex-wrap gap-1.5">
                  {entities.sections.map((sec, i) => (
                    <span
                      key={i}
                      className="bg-ivory-50 text-burgundy-900 font-mono font-bold border border-ivory-300 px-2.5 py-1 rounded"
                    >
                      {sec}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {((entities.courts && entities.courts.length > 0) ||
        (entities.citations && entities.citations.length > 0)) && (
        <div className="bg-white border border-gold-500/30 rounded p-5 parchment-card space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-gold-600" />
            <span>Forums &amp; Cited Reports</span>
          </h4>
          <div className="flex flex-wrap gap-2 text-xs">
            {(entities.courts || []).map((c, i) => (
              <span
                key={`c-${i}`}
                className="bg-navy-50 text-navy-900 border border-navy-200 px-2.5 py-1 rounded font-medium"
              >
                {c}
              </span>
            ))}
            {(entities.citations || []).map((cit, i) => (
              <span
                key={`cit-${i}`}
                className="bg-ivory-100 text-burgundy-900 border border-gold-400 px-2.5 py-1 rounded font-mono font-semibold"
              >
                {cit}
              </span>
            ))}
          </div>
        </div>
      )}

      {entities.legalTerms && entities.legalTerms.length > 0 && (
        <div className="bg-white border border-gold-500/30 rounded p-5 parchment-card space-y-3">
          <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-burgundy-900 flex items-center gap-1.5">
            <Bookmark className="w-3.5 h-3.5 text-gold-600" />
            <span>Doctrinal &amp; Procedural Concepts</span>
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {entities.legalTerms.map((item, i) => (
              <div key={i} className="bg-ivory-50 p-3 rounded border border-ivory-300">
                <span className="font-serif font-bold text-navy-900 flex items-center gap-1">
                  <Scale className="w-3 h-3 text-gold-600" />
                  {item.term}
                </span>
                <p className="text-charcoal-700 mt-1 leading-relaxed">{item.definition}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
