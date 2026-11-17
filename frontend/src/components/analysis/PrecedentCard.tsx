import React, { useState } from 'react';
import { Precedent, ISupportingJudgmentPassage } from '../../types';
import {
  Bookmark,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Scale,
  Calendar,
  Landmark,
  HelpCircle,
  Gavel,
  Layers
} from 'lucide-react';

interface PrecedentCardProps {
  precedent: Precedent;
  rank?: number;
  matchingPassage?: ISupportingJudgmentPassage;
  onBookmark?: (precedent: Precedent) => void;
  isBookmarked?: boolean;
}

export const PrecedentCard: React.FC<PrecedentCardProps> = ({
  precedent,
  rank,
  matchingPassage,
  onBookmark,
  isBookmarked = false
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showSignals, setShowSignals] = useState(false);
  const [showWhyMatches, setShowWhyMatches] = useState(false);

  const relevanceBadgeStyle = (cls?: string) => {
    switch (cls) {
      case 'Directly relevant':
        return 'bg-navy-900 text-gold-300 border-gold-500/40';
      case 'Potentially adverse authority':
        return 'bg-burgundy-50 text-burgundy-900 border-burgundy-300';
      case 'Distinguishing authority':
        return 'bg-gold-100 text-gold-900 border-gold-400';
      case 'Constitutional background':
        return 'bg-ivory-200 text-navy-900 border-gold-400';
      default:
        return 'bg-ivory-100 text-charcoal-800 border-ivory-400';
    }
  };

  return (
    <div className="parchment-card rounded p-5 space-y-3.5 transition-colors hover:border-gold-500">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {typeof rank === 'number' && (
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-navy-950 text-gold-300 border border-gold-500/40">
                Rank #{rank}
              </span>
            )}

            {precedent.relevanceClassification && (
              <span
                className={`text-[10.5px] font-semibold px-2.5 py-0.5 rounded border ${relevanceBadgeStyle(
                  precedent.relevanceClassification
                )}`}
              >
                {precedent.relevanceClassification}
              </span>
            )}

            {precedent.officialSourceVerified ? (
              <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2.5 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">
                <CheckCircle2 className="w-3 h-3 text-navy-800" />
                <span>Official Source Verified</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2.5 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-300">
                <AlertTriangle className="w-3 h-3 text-burgundy-800" />
                <span>Official source not verified</span>
              </span>
            )}
          </div>

          <h4 className="text-base font-serif font-bold text-navy-900 leading-snug">
            {precedent.caseTitle}
          </h4>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-charcoal-600 font-sans">
            <span className="inline-flex items-center gap-1 font-medium text-burgundy-900">
              <Scale className="w-3.5 h-3.5 text-gold-600 shrink-0" />
              {precedent.citation}
            </span>
            <span className="inline-flex items-center gap-1">
              <Landmark className="w-3.5 h-3.5 text-gold-600 shrink-0" />
              {precedent.court}
            </span>
            {precedent.judgmentDate && (
              <span className="inline-flex items-center gap-1 font-mono text-[11px]">
                <Calendar className="w-3.5 h-3.5 text-gold-600 shrink-0" />
                {precedent.judgmentDate}
              </span>
            )}
          </div>
        </div>

        {onBookmark && (
          <button
            type="button"
            onClick={() => onBookmark(precedent)}
            className={`self-start shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              isBookmarked
                ? 'bg-navy-900 text-gold-300 border-gold-500'
                : 'bg-ivory-50 text-navy-900 border-ivory-400 hover:border-gold-500'
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            <span>{isBookmarked ? 'Saved' : 'Save Authority'}</span>
          </button>
        )}
      </div>

      {/* Expandable "Why this precedent matches" */}
      <div className="border border-gold-500/30 rounded overflow-hidden">
        <button
          type="button"
          onClick={() => setShowWhyMatches((w) => !w)}
          className="w-full flex items-center justify-between px-3.5 py-2 bg-ivory-50 hover:bg-ivory-100/70 transition-colors text-xs font-serif font-semibold text-navy-900"
        >
          <span className="flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-gold-700" />
            <span>Why this precedent matches (Doctrinal &amp; Factual Rationale)</span>
          </span>
          {showWhyMatches ? (
            <ChevronUp className="w-3.5 h-3.5 text-gold-700" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-gold-700" />
          )}
        </button>
        {showWhyMatches && (
          <div className="p-3.5 bg-white border-t border-gold-500/20 space-y-2 text-xs text-charcoal-700 leading-relaxed font-sans">
            <p>
              {precedent.retrievalReason ||
                precedent.retrievalSignals?.relevanceExplanation ||
                'Identified via hybrid multi-modal retrieval matching governing statutory provisions and factual triggers.'}
            </p>
            {precedent.outcomeRationale && (
              <p className="pt-1.5 border-t border-ivory-200">
                <strong className="font-serif text-navy-900">Operative Rationale: </strong>
                {precedent.outcomeRationale}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Matching Judgment Passage with Paragraph Reference */}
      {(matchingPassage || precedent.ratioPrinciple) && (
        <div className="bg-ivory-50 border-l-2 border-l-burgundy-900 p-3.5 rounded-r space-y-1.5 text-xs">
          <div className="flex items-center justify-between flex-wrap gap-1">
            <div className="flex items-center gap-1.5 font-serif font-bold text-burgundy-950">
              <Gavel className="w-3.5 h-3.5 text-gold-700 shrink-0" />
              <span>
                Matching Judgment Passage{' '}
                {matchingPassage?.paragraphNumber
                  ? `(Para ${matchingPassage.paragraphNumber})`
                  : ''}
              </span>
            </div>
            {matchingPassage && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-white text-charcoal-700 border border-ivory-300">
                {matchingPassage.isDirectQuote
                  ? 'Character-Verified Verbatim Quote'
                  : 'Editorial Paraphrase'}
              </span>
            )}
          </div>
          {matchingPassage?.pinpointCitation && (
            <span className="font-serif text-[11px] font-semibold text-burgundy-900 block">
              Pinpoint Citation: {matchingPassage.pinpointCitation}
            </span>
          )}
          <p className="font-serif italic text-charcoal-900 leading-relaxed pt-0.5">
            &ldquo;
            {matchingPassage?.verbatimQuote ||
              matchingPassage?.editorialParaphrase ||
              precedent.ratioPrinciple ||
              precedent.summary}
            &rdquo;
          </p>
        </div>
      )}

      {/* Legal Provisions Tags */}
      {precedent.legalProvisions && precedent.legalProvisions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {precedent.legalProvisions.map((prov, idx) => (
            <span
              key={idx}
              className="text-[11px] font-medium bg-ivory-100 text-navy-900 border border-gold-500/30 px-2 py-0.5 rounded"
            >
              {prov}
            </span>
          ))}
        </div>
      )}

      {/* Summary */}
      <p className="text-xs text-charcoal-700 leading-relaxed font-sans">{precedent.summary}</p>

      {/* Expandable Retrieval Signal Breakdown */}
      <div>
        <button
          type="button"
          onClick={() => setShowSignals((s) => !s)}
          className="inline-flex items-center gap-1 text-xs font-serif font-semibold text-navy-800 hover:text-gold-700 transition-colors"
        >
          {showSignals ? <ChevronUp className="w-3.5 h-3.5 text-gold-600" /> : <ChevronDown className="w-3.5 h-3.5 text-gold-600" />}
          <span>{showSignals ? 'Hide Retrieval Signals & Modality Contributions' : 'View Retrieval Signals & Modality Contributions (Hybrid RRF)'}</span>
        </button>

        {showSignals && (
          <div className="mt-2 bg-ivory-50 border border-ivory-300 rounded p-3 text-xs text-charcoal-700 space-y-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-serif font-semibold text-navy-900 flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-gold-700" />
                <span>RRF Fusion Score:</span>
              </span>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">
                {precedent.retrievalSignals?.rrfScore !== undefined
                  ? precedent.retrievalSignals.rrfScore.toFixed(4)
                  : (precedent.similarityScore ? precedent.similarityScore.toFixed(4) : 'Computed')}
              </span>
              <span className="font-serif font-semibold text-navy-900">
                Active Modalities:
              </span>
              <span className="text-charcoal-600 font-sans">
                {precedent.retrievalSignals?.activeModalities?.join(', ') || 'TF-IDF, BM25'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 border-t border-ivory-200 text-[11px]">
              <div className="bg-white p-2 rounded border border-ivory-300">
                <span className="text-charcoal-500 block">TF-IDF Lexical</span>
                <span className="font-semibold text-navy-900">
                  {precedent.retrievalSignals?.tfidfRank !== undefined
                    ? `Rank #${precedent.retrievalSignals.tfidfRank}`
                    : 'Matched via Lexical Index'}
                </span>
              </div>
              <div className="bg-white p-2 rounded border border-ivory-300">
                <span className="text-charcoal-500 block">BM25 Probabilistic</span>
                <span className="font-semibold text-navy-900">
                  {precedent.retrievalSignals?.bm25Rank !== undefined
                    ? `Rank #${precedent.retrievalSignals.bm25Rank}`
                    : 'Matched via Lexical Index'}
                </span>
              </div>
              <div className="bg-white p-2 rounded border border-ivory-300">
                <span className="text-charcoal-500 block">Dense Semantic (BGE)</span>
                <span className="font-semibold text-charcoal-700">
                  {precedent.retrievalSignals?.semanticRank !== undefined
                    ? `Rank #${precedent.retrievalSignals.semanticRank}`
                    : 'Offline / Serverless Mode'}
                </span>
              </div>
            </div>

            {((precedent.matchedTerms && precedent.matchedTerms.length > 0) ||
              (precedent.retrievalSignals?.matchedKeywords && precedent.retrievalSignals.matchedKeywords.length > 0)) && (
              <div className="pt-1 flex flex-wrap items-center gap-1.5">
                <span className="font-serif font-semibold text-navy-900 text-[11px]">Matched Keywords:</span>
                {(precedent.retrievalSignals?.matchedKeywords || precedent.matchedTerms || []).map((term, tIdx) => (
                  <span
                    key={tIdx}
                    className="font-mono text-[10.5px] px-1.5 py-0.5 rounded bg-ivory-100 text-charcoal-800 border border-ivory-300"
                  >
                    {term}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Expandable Article 141 Ratio, Obiter & Subsequent Treatment */}
      {(precedent.article141Status ||
        precedent.obiterAndScopeNote ||
        precedent.subsequentTreatment ||
        precedent.judgmentText) && (
        <div>
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="inline-flex items-center gap-1 text-xs font-serif font-semibold text-burgundy-900 hover:text-navy-900 transition-colors"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <span>{expanded ? 'Hide Ratio, Bench & Treatment Analysis' : 'View Ratio, Bench & Subsequent Treatment'}</span>
          </button>

          {expanded && (
            <div className="mt-3 space-y-2.5 bg-ivory-50 border border-ivory-300 rounded p-4 text-xs text-charcoal-700 leading-relaxed">
              {precedent.bench && (
                <p>
                  <strong className="font-serif text-navy-900">Bench / Coram: </strong>
                  {precedent.bench}
                </p>
              )}
              {precedent.article141Status && (
                <p>
                  <strong className="font-serif text-navy-900">Article 141 / Binding Ratio: </strong>
                  {precedent.article141Status}
                </p>
              )}
              {precedent.obiterAndScopeNote && (
                <p>
                  <strong className="font-serif text-navy-900">Obiter &amp; Factual Scope: </strong>
                  {precedent.obiterAndScopeNote}
                </p>
              )}
              {precedent.subsequentTreatment && (
                <p>
                  <strong className="font-serif text-navy-900">Subsequent Judicial Treatment: </strong>
                  {precedent.subsequentTreatment}
                </p>
              )}
              {precedent.judgmentText && (
                <p className="pt-1 border-t border-ivory-300 text-charcoal-600">{precedent.judgmentText}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Verification Note + Explicit Official & Secondary Source Links */}
      <div className="pt-2.5 border-t border-ivory-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {precedent.officialSourceVerified && precedent.officialSourceUrl ? (
            <a
              href={precedent.officialSourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold text-navy-900 hover:text-burgundy-900 underline underline-offset-2"
            >
              <ExternalLink className="w-3.5 h-3.5 text-gold-700" />
              <span>{precedent.officialSourceLabel || 'Official Court Judgment (PDF)'}</span>
            </a>
          ) : null}

          {precedent.secondaryReferenceUrl && (
            <a
              href={precedent.secondaryReferenceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-medium text-burgundy-900 hover:text-navy-900 underline underline-offset-2"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>{precedent.secondaryReferenceLabel || 'Indian Kanoon Secondary Reference'}</span>
            </a>
          )}

          {!precedent.officialSourceUrl && !precedent.secondaryReferenceUrl && precedent.sourceUrl && (
            <a
              href={precedent.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-medium text-navy-900 hover:text-burgundy-900 underline underline-offset-2"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open Reference Record</span>
            </a>
          )}
        </div>

        {precedent.verificationNote && (
          <span className="text-[11px] text-charcoal-500">{precedent.verificationNote}</span>
        )}
      </div>
    </div>
  );
};
