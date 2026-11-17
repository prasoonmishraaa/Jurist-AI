import React, { useState } from 'react';
import { IEvidenceTraceNode } from '../../types';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Scale,
  BookOpen,
  ScrollText,
  Gavel,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  Layers,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react';

interface EvidenceTraceViewProps {
  traceNodes?: IEvidenceTraceNode[];
  documentMetadata?: any;
}

/**
 * Renders document text with low-confidence OCR tokens [?token?] highlighted in amber
 * with hover tooltips instructing counsel to verify against paper copies.
 */
export const renderTextWithOcrWarnings = (text: string) => {
  if (!text) return null;
  const parts = text.split(/(\[\?[^?]+\?\])/g);
  return parts.map((part, idx) => {
    const match = part.match(/^\[\?([^?]+)\?\]$/);
    if (match) {
      const token = match[1];
      return (
        <span
          key={idx}
          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 mx-0.5 text-xs font-mono font-medium rounded bg-amber-100 text-amber-950 border border-amber-400 border-dashed cursor-help"
          title="Low-confidence OCR extraction. Verify against the original document."
        >
          <AlertTriangle className="w-3 h-3 text-amber-700 shrink-0 inline" />
          <span>{token}</span>
        </span>
      );
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
};

export const EvidenceTraceView: React.FC<EvidenceTraceViewProps> = ({
  traceNodes,
  documentMetadata
}) => {
  const [expandedExplanations, setExpandedExplanations] = useState<Record<string, boolean>>({});

  const toggleExplanation = (traceId: string) => {
    setExpandedExplanations((prev) => ({
      ...prev,
      [traceId]: !prev[traceId]
    }));
  };

  if (!traceNodes || traceNodes.length === 0) {
    return (
      <div className="parchment-card rounded p-8 text-center space-y-3">
        <FileCheck className="w-10 h-10 text-gold-600 mx-auto" />
        <h3 className="text-base font-serif font-bold text-navy-900">
          Evidence Traceability Graph Unavailable
        </h3>
        <p className="text-xs text-charcoal-500 max-w-md mx-auto leading-relaxed">
          This case record does not contain an evidence trace graph. Traceability links are automatically assembled when documents are analyzed with structured legal arguments and verifiable authorities.
        </p>
      </div>
    );
  }

  const getClassificationBadge = (classification: string, isContested?: boolean) => {
    switch (classification) {
      case 'User-provided fact':
        return (
          <span className="font-semibold px-2.5 py-0.5 rounded border text-[10.5px] bg-green-50 text-green-900 border-green-300">
            Admitted / User-Provided Fact
          </span>
        );
      case 'Party allegation':
        return (
          <span className="font-semibold px-2.5 py-0.5 rounded border text-[10.5px] bg-burgundy-50 text-burgundy-900 border-burgundy-300">
            Party Allegation {isContested ? '(Contested by Opponent)' : '(Unadmitted)'}
          </span>
        );
      case 'Material fact':
        return (
          <span className="font-semibold px-2.5 py-0.5 rounded border text-[10.5px] bg-navy-50 text-navy-900 border-navy-300">
            Material Fact on Record
          </span>
        );
      default:
        return (
          <span className="font-semibold px-2.5 py-0.5 rounded border text-[10.5px] bg-gold-50 text-gold-950 border-gold-300">
            Inferred Legal Connection
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="parchment-card rounded p-5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-2.5">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-gold-600" />
            <h3 className="text-sm font-serif font-bold text-navy-900 uppercase tracking-wide">
              Explainable AI: End-to-End Evidence Traceability Chain
            </h3>
          </div>
          <span className="text-xs font-serif font-semibold text-charcoal-600">
            {traceNodes.length} Verifiable Ground{traceNodes.length > 1 ? 's' : ''} Mapped
          </span>
        </div>
        <p className="text-xs text-charcoal-600 leading-relaxed font-sans">
          Each ground traces causal provenance from the originating <strong>Document Passage</strong>, to the classified <strong>Fact / Allegation</strong>, governing <strong>Legal Issue</strong>, applicable <strong>Statute</strong>, retrieved <strong>Precedent Authority</strong>, pinpoint <strong>Judgment Passage</strong>, and resulting <strong>Draft Submission</strong>. Unresolved relationships are explicitly labeled.
        </p>

        {/* Visual Provenance Flow Legend */}
        <div className="pt-2 border-t border-ivory-200 flex flex-wrap items-center gap-2 text-[11px] font-sans text-charcoal-700">
          <span className="font-serif font-bold text-navy-900">Chain Provenance:</span>
          <span className="px-2 py-0.5 rounded bg-ivory-100 border border-ivory-300">1. Document Snippet</span>
          <ArrowRight className="w-3 h-3 text-gold-600" />
          <span className="px-2 py-0.5 rounded bg-green-50 text-green-950 border border-green-200">2. Fact / Allegation</span>
          <ArrowRight className="w-3 h-3 text-gold-600" />
          <span className="px-2 py-0.5 rounded bg-ivory-100 border border-ivory-300">3. Statute &amp; Regime</span>
          <ArrowRight className="w-3 h-3 text-gold-600" />
          <span className="px-2 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">4. Precedent &amp; Passage</span>
          <ArrowRight className="w-3 h-3 text-gold-600" />
          <span className="px-2 py-0.5 rounded bg-gold-50 text-gold-950 border border-gold-300">5. Draft Submission</span>
        </div>
      </div>

      {/* Trace Nodes */}
      {traceNodes.map((node) => {
        const isUncertain = node.confidenceAssessment.isOcrUncertain;
        const reliability = node.confidenceAssessment.overallTraceReliability;
        const unresolved = node.unresolvedRelationships || [];
        const isExplanationOpen = Boolean(expandedExplanations[node.traceId]);

        return (
          <div
            key={node.traceId}
            className={`parchment-card rounded p-6 space-y-5 border transition-colors ${
              isUncertain
                ? 'border-amber-400/80 bg-amber-50/20'
                : 'border-ivory-300 hover:border-gold-500'
            }`}
          >
            {/* Header / Ground Bar */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-ivory-200 pb-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-serif font-bold text-sm px-2.5 py-0.5 rounded bg-navy-950 text-gold-300 border border-gold-500/30">
                    {node.groundNumber}
                  </span>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-ivory-100 text-charcoal-600 border border-ivory-300">
                    {node.traceId}
                  </span>

                  {/* Reliability Badge */}
                  {reliability === 'high_confidence' && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-green-50 text-green-800 border border-green-200">
                      <CheckCircle2 className="w-3 h-3 text-green-700" />
                      <span>High Confidence Trace</span>
                    </span>
                  )}
                  {reliability === 'moderate_confidence' && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-navy-50 text-navy-800 border border-navy-200">
                      <CheckCircle2 className="w-3 h-3 text-navy-700" />
                      <span>Moderate Confidence</span>
                    </span>
                  )}
                  {reliability === 'requires_verification' && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                      <ShieldAlert className="w-3 h-3 text-amber-800" />
                      <span>Requires Verification (OCR Uncertainty)</span>
                    </span>
                  )}
                </div>

                <h4 className="text-base font-serif font-bold text-navy-900 pt-0.5">
                  {node.legalIssueTitle || 'Legal Issue Formulation'}
                </h4>
              </div>

              {/* Unresolved Relationships Warning */}
              {unresolved.length > 0 && (
                <div className="flex flex-wrap items-center gap-1 self-start">
                  {unresolved.map((item, uIdx) => (
                    <span
                      key={uIdx}
                      className="inline-flex items-center gap-1 text-[10.5px] font-medium px-2 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-200"
                    >
                      <HelpCircle className="w-3 h-3 text-burgundy-700" />
                      <span>Unresolved: {item.replace(/_/g, ' ')}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* OCR Caveat Alert if applicable */}
            {isUncertain && node.confidenceAssessment.ocrReliabilityCaveat && (
              <div className="bg-amber-100/90 border-l-4 border-l-amber-600 p-3.5 rounded-r text-xs text-amber-950 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-800 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <strong className="font-serif font-bold text-amber-950 block">
                    OCR Uncertainty Gate Alert
                  </strong>
                  <p className="leading-relaxed">
                    {node.confidenceAssessment.ocrReliabilityCaveat}
                  </p>
                </div>
              </div>
            )}

            {/* Expandable Explanation for this Ground Finding */}
            <div className="border border-gold-500/30 rounded overflow-hidden">
              <button
                type="button"
                onClick={() => toggleExplanation(node.traceId)}
                className="w-full flex items-center justify-between px-3.5 py-2 bg-ivory-50 hover:bg-ivory-100/80 transition-colors text-xs font-serif font-semibold text-navy-900"
              >
                <span className="flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-gold-700" />
                  <span>Explain Finding &amp; Causal Provenance Reasoning</span>
                </span>
                {isExplanationOpen ? (
                  <ChevronUp className="w-3.5 h-3.5 text-gold-700" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-gold-700" />
                )}
              </button>

              {isExplanationOpen && (
                <div className="p-4 bg-white border-t border-gold-500/20 text-xs text-charcoal-700 space-y-2.5 leading-relaxed font-sans">
                  <p>
                    <strong className="font-serif text-navy-900">Causal Logic: </strong>
                    The factual assertion (categorized as <em>{node.factAssertion.classification}</em>) directly invokes statutory scrutiny under <strong>{node.statutoryProvision}</strong> ({node.statutoryRegime.replace(/_/g, ' ')}).
                  </p>
                  {node.precedent && (
                    <p>
                      <strong className="font-serif text-navy-900">Precedential Basis: </strong>
                      Authority <em>{node.precedent.caseTitle}</em> ({node.precedent.citation}) is linked because its ratio decidendi governs this specific statutory test.
                      {node.judgmentPassage?.paragraphNumber && ` Pinpoint passage isolates Para ${node.judgmentPassage.paragraphNumber}.`}
                    </p>
                  )}
                  <p className="text-[11px] text-charcoal-500 italic pt-1 border-t border-ivory-200">
                    Verification Status: {node.sourcePassage.attributionStatus === 'verified' ? 'Origin page verified on record' : 'Origin unverified'}. Precedent verified directly against authoritative court record.
                  </p>
                </div>
              )}
            </div>

            {/* The 6-Step Evidence Breadcrumb Chain */}
            <div className="space-y-3.5 text-xs">
              {/* STEP 1: Original Document Passage */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ivory-200 pb-1.5 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <FileText className="w-3.5 h-3.5 text-gold-700" />
                    <span>Step 1: Uploaded Document Passage</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-charcoal-600">
                      📄 {node.sourcePassage.documentName || 'Uploaded File'}
                    </span>
                    <span className="font-semibold text-navy-900 px-1.5 py-0.5 rounded bg-ivory-100 border border-ivory-300">
                      {node.sourcePassage.pageNumber ? `Page ${node.sourcePassage.pageNumber}` : 'Page Unresolved'}
                    </span>
                    <span className="font-mono text-[10.5px] px-1.5 py-0.5 rounded bg-ivory-100 text-charcoal-700 border border-ivory-300">
                      {node.sourcePassage.extractionMethod === 'ocr' ? 'Tesseract OCR' : 'Native Digital'}
                    </span>
                    {node.sourcePassage.pageConfidence !== null && node.sourcePassage.pageConfidence !== undefined && (
                      <span
                        className={`font-mono text-[10.5px] px-1.5 py-0.5 rounded border ${
                          node.sourcePassage.pageConfidence < 0.75
                            ? 'bg-amber-100 text-amber-900 border-amber-300'
                            : 'bg-green-50 text-green-800 border-green-200'
                        }`}
                      >
                        {Math.round(node.sourcePassage.pageConfidence * 100)}% Conf.
                      </span>
                    )}
                  </div>
                </div>
                <div className="p-2.5 rounded bg-ivory-50 border border-ivory-200 font-sans text-charcoal-800 leading-relaxed italic">
                  &ldquo;{renderTextWithOcrWarnings(node.sourcePassage.textSnippet)}&rdquo;
                </div>
              </div>

              {/* STEP 2: Fact / Allegation Classification */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-1.5">
                <div className="flex items-center justify-between gap-2 border-b border-ivory-200 pb-1 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <ArrowRight className="w-3 h-3 text-gold-700" />
                    <span>Step 2: Fact vs Allegation Classification</span>
                  </div>
                  {getClassificationBadge(node.factAssertion.classification, node.factAssertion.isContested)}
                </div>
                <p className="text-charcoal-800 leading-relaxed font-sans pt-0.5">
                  {renderTextWithOcrWarnings(node.factAssertion.statement)}
                </p>
              </div>

              {/* STEP 3: Statutory Provision & Regime */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-1.5">
                <div className="flex items-center justify-between gap-2 border-b border-ivory-200 pb-1 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <Scale className="w-3.5 h-3.5 text-gold-700" />
                    <span>Step 3: Applicable Statutory Provision &amp; Regime</span>
                  </div>
                  <span className="font-mono text-[10.5px] px-2 py-0.5 rounded bg-ivory-100 text-charcoal-700 border border-ivory-300">
                    {node.statutoryRegime.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="font-serif font-semibold text-burgundy-900 pt-0.5">
                  {node.statutoryProvision}
                </p>
              </div>

              {/* STEP 4: Precedent Authority & Retrieval Breakdown */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-2">
                <div className="flex items-center justify-between gap-2 border-b border-ivory-200 pb-1 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <BookOpen className="w-3.5 h-3.5 text-gold-700" />
                    <span>Step 4: Relevant Precedent Authority</span>
                  </div>
                  {node.precedent?.officialSourceVerified ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">
                      <CheckCircle2 className="w-3 h-3 text-navy-800" />
                      <span>Official Source Verified</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-300">
                      <AlertTriangle className="w-3 h-3 text-burgundy-800" />
                      <span>Official Source Unverified</span>
                    </span>
                  )}
                </div>

                {node.precedent ? (
                  <div className="space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                      <div>
                        <h5 className="font-serif font-bold text-navy-900 text-sm">
                          {node.precedent.caseTitle}
                        </h5>
                        <p className="text-xs text-charcoal-600 font-sans">
                          {node.precedent.citation} &bull; {node.precedent.court}
                        </p>
                      </div>
                      {node.precedent.officialSourceUrl && (
                        <a
                          href={node.precedent.officialSourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-navy-900 hover:text-burgundy-900 underline"
                        >
                          <ExternalLink className="w-3 h-3 text-gold-700" />
                          <span>Official Judgment PDF</span>
                        </a>
                      )}
                    </div>

                    {/* Retrieval Signal Breakdown */}
                    {node.precedent.signals && (
                      <div className="bg-ivory-50 rounded p-2.5 border border-ivory-200 space-y-1 text-[11px]">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span className="font-serif font-semibold text-navy-900">
                            Hybrid RRF Score:
                          </span>
                          <span className="font-mono text-xs px-1.5 py-0.2 rounded bg-white text-navy-900 border border-navy-200">
                            {node.precedent.signals.rrfScore !== undefined
                              ? node.precedent.signals.rrfScore.toFixed(4)
                              : 'N/A'}
                          </span>
                          <span className="font-serif font-semibold text-navy-900">
                            Modalities:
                          </span>
                          <span className="text-charcoal-600">
                            TF-IDF {node.precedent.signals.tfidfRank ? `(#${node.precedent.signals.tfidfRank})` : ''} &bull; BM25 {node.precedent.signals.bm25Rank ? `(#${node.precedent.signals.bm25Rank})` : ''} &bull; Dense Semantic (Offline)
                          </span>
                        </div>
                        {node.precedent.signals.matchedKeywords && node.precedent.signals.matchedKeywords.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1 pt-1">
                            <span className="text-charcoal-500 font-serif">Matched Keywords:</span>
                            {node.precedent.signals.matchedKeywords.map((kw, kwIdx) => (
                              <span
                                key={kwIdx}
                                className="font-mono text-[10px] px-1 py-0.2 rounded bg-white text-charcoal-700 border border-ivory-300"
                              >
                                {kw}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-charcoal-500 italic">
                    Precedent authority relationship is unresolved for this ground.
                  </p>
                )}
              </div>

              {/* STEP 5: Supporting Judgment Passage */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-2">
                <div className="flex items-center justify-between gap-2 border-b border-ivory-200 pb-1 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <Gavel className="w-3.5 h-3.5 text-gold-700" />
                    <span>Step 5: Supporting Judgment Passage</span>
                  </div>
                  {node.judgmentPassage?.verificationStatus === 'unverified' ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-300">
                      <ShieldAlert className="w-3 h-3 text-amber-700" />
                      <span>Unverified Authority (Pending Primary Verification)</span>
                    </span>
                  ) : node.judgmentPassage?.isDirectQuote && node.judgmentPassage?.verificationStatus === 'character_verified' ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-green-50 text-green-900 border border-green-300">
                      <CheckCircle2 className="w-3 h-3 text-green-700" />
                      <span>Character-Verified Verbatim Quotation</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-ivory-100 text-charcoal-700 border border-ivory-300">
                      <span>Editorial Paraphrase (No Direct Quote Claimed)</span>
                    </span>
                  )}
                </div>

                {node.judgmentPassage ? (
                  <div className="space-y-1.5">
                    {node.judgmentPassage.pinpointCitation && (
                      <p className="font-serif font-bold text-burgundy-900 text-xs">
                        {node.judgmentPassage.pinpointCitation}
                      </p>
                    )}
                    {node.judgmentPassage.isDirectQuote && node.judgmentPassage.verbatimQuote && (
                      <blockquote className="p-2.5 rounded bg-ivory-50 border-l-2 border-l-navy-900 text-charcoal-900 italic font-serif leading-relaxed">
                        &ldquo;{node.judgmentPassage.verbatimQuote}&rdquo;
                      </blockquote>
                    )}
                    <p className="text-charcoal-700 font-sans leading-relaxed text-xs">
                      <strong className="font-serif text-navy-900">Principle / Paraphrase: </strong>
                      {node.judgmentPassage.editorialParaphrase}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-charcoal-500 italic">
                    Supporting judgment passage relationship is unresolved.
                  </p>
                )}
              </div>

              {/* STEP 6: Draft Court Submission */}
              <div className="bg-white rounded border border-ivory-300 p-3.5 space-y-1.5">
                <div className="flex items-center justify-between gap-2 border-b border-ivory-200 pb-1 text-[11px]">
                  <div className="flex items-center gap-1.5 font-serif font-bold text-navy-900">
                    <ScrollText className="w-3.5 h-3.5 text-gold-700" />
                    <span>Step 6: Resulting Draft Court Submission</span>
                  </div>
                  <span className="font-mono text-[10.5px] px-2 py-0.5 rounded bg-ivory-100 text-charcoal-600 border border-ivory-300">
                    {node.argumentId}
                  </span>
                </div>
                <p className="font-serif text-xs text-charcoal-800 leading-relaxed pt-0.5 whitespace-pre-line">
                  {node.draftSubmissionSnippet || 'Refer to Submissions tab for complete draft ground.'}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
