import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Scale,
  ArrowLeft,
  Printer,
  AlertTriangle,
  BookOpen,
  Clock,
  ScrollText,
  Download,
  Save,
  Check,
  FileCode2,
  FileText,
  Gavel,
  StickyNote,
  Layers
} from 'lucide-react';
import { api } from '../services/api';
import { CaseAnalysis, Precedent } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { PrecedentCard } from '../components/analysis/PrecedentCard';
import { JudicialTreatmentView } from '../components/analysis/JudicialTreatmentView';
import { LegalIssueCard } from '../components/analysis/LegalIssueCard';
import { EntityBadgesView } from '../components/analysis/EntityBadge';
import { LegalArgumentsView } from '../components/analysis/LegalArgumentsView';
import { CaseFactsSynthesisView } from '../components/analysis/CaseFactsSynthesisView';
import { ApplicableLawView } from '../components/analysis/ApplicableLawView';
import { EvidenceTraceView } from '../components/analysis/EvidenceTraceView';
import { DocumentIntelligenceView } from '../components/analysis/DocumentIntelligenceView';

type TabKey =
  | 'overview'
  | 'document'
  | 'law'
  | 'issues'
  | 'precedents'
  | 'arguments'
  | 'evidence'
  | 'treatment'
  | 'notes';

export const AnalysisResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<CaseAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [researchNotes, setResearchNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!id) return;
      try {
        const [data, saved] = await Promise.all([
          api.getAnalysisById(id),
          api.getSavedCases().catch(() => [])
        ]);
        setAnalysis(data);
        setResearchNotes(data.researchNotes || '');
        const savedCodes = new Set<string>(
          (saved || []).map((s: any) => s.precedentCode || s.caseTitle).filter(Boolean)
        );
        setBookmarkedIds(savedCodes);
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Failed to retrieve research dossier.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnalysis();
  }, [id]);

  const handleSaveDraft = async (groundId: string, editedText: string) => {
    if (!analysis) return;
    const analysisId = analysis.id || analysis._id!;
    const updated = await api.updateAnalysis(analysisId, {
      editedDrafts: { [groundId]: editedText }
    });
    setAnalysis(updated);
    setActionMessage('Draft submission saved to dossier.');
    setTimeout(() => setActionMessage(null), 2500);
  };

  const handleSaveNotes = async () => {
    if (!analysis) return;
    try {
      setSavingNotes(true);
      const analysisId = analysis.id || analysis._id!;
      const updated = await api.updateAnalysis(analysisId, { researchNotes });
      setAnalysis(updated);
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2500);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleBookmarkPrecedent = async (precedent: Precedent) => {
    if (!analysis) return;
    try {
      await api.saveCase({
        precedentId: precedent.id,
        precedentCode: precedent.id,
        analysisId: analysis.id || analysis._id,
        caseTitle: precedent.caseTitle,
        court: precedent.court,
        citation: precedent.citation,
        officialSourceUrl: precedent.officialSourceUrl,
        officialSourceVerified: precedent.officialSourceVerified,
        secondaryReferenceUrl: precedent.secondaryReferenceUrl,
        sourceUrl: precedent.sourceUrl,
        category: precedent.category
      });
      setBookmarkedIds((prev) => {
        const next = new Set(prev);
        if (precedent.id) next.add(precedent.id);
        next.add(precedent.caseTitle);
        return next;
      });
      setActionMessage(`Saved "${precedent.caseTitle}" to Bookmarked Authorities.`);
      setTimeout(() => setActionMessage(null), 3000);
    } catch {
      setActionMessage('Unable to bookmark authority right now.');
    }
  };

  const buildExportMarkdown = (doc: CaseAnalysis): string => {
    const lines: string[] = [];
    lines.push(`# ${doc.caseTitle}`);
    lines.push(`**Forum:** ${doc.court} | **Domain:** ${doc.category}`);
    lines.push(`**Prepared:** ${new Date(doc.createdAt).toLocaleDateString('en-IN')}`);
    lines.push('');
    lines.push('## 1. Dispute Narrative Excerpt');
    lines.push(doc.inputTextSnippet);
    lines.push('');
    if (doc.applicableLaw) {
      lines.push('## 2. Applicable Legislation Assessment');
      lines.push(doc.applicableLaw.regimeSummary);
      lines.push('');
      doc.applicableLaw.substantiveLaw.forEach((s) => {
        lines.push(`- **${s.provision}** (${s.statute}): ${s.applicabilityNote}`);
      });
      doc.applicableLaw.proceduralLaw.forEach((p) => {
        lines.push(`- **${p.provision}** (${p.statute}): ${p.applicabilityNote}`);
      });
      lines.push('');
    }
    if (doc.legalIssues?.length) {
      lines.push('## 3. Questions of Law');
      doc.legalIssues.forEach((q, idx) => {
        lines.push(`${idx + 1}. **${q.issue}** — *${q.statutoryProvision}*`);
        lines.push(`   ${q.whyIssueMatters || q.description}`);
      });
      lines.push('');
    }
    if (doc.similarCases?.length) {
      lines.push('## 4. Precedent Authorities');
      doc.similarCases.forEach((p) => {
        lines.push(`- **${p.caseTitle}** [${p.citation}] (${p.court})`);
        lines.push(`  - Source Status: ${p.officialSourceVerified ? `Official Verified (${p.officialSourceUrl})` : `Official source not verified — Secondary Reference: ${p.secondaryReferenceUrl || p.sourceUrl}`}`);
        lines.push(`  - Summary: ${p.summary}`);
      });
      lines.push('');
    }
    if (doc.legalArguments?.length) {
      lines.push('## 5. Draft Submissions & Opposing Arguments');
      doc.legalArguments.forEach((arg) => {
        const draftBody = doc.editedDrafts?.[arg.id] || arg.suggestedSubmission;
        lines.push(`### ${arg.groundNumber}: ${arg.heading}`);
        lines.push(`**Proposition:** ${arg.legalProposition}`);
        lines.push('');
        lines.push('**Draft Submission:**');
        lines.push(draftBody);
        lines.push('');
        if (arg.counterarguments?.length) {
          lines.push('**Opposing Arguments & Rebuttals:**');
          arg.counterarguments.forEach((c) => {
            lines.push(`- *${c.opposingGround}*: ${c.rebuttalStrategy}`);
          });
        }
        lines.push('');
      });
    }
    if (doc.evidenceTraceGraph?.length) {
      lines.push('## 6. End-to-End Evidence Traceability Chain');
      doc.evidenceTraceGraph.forEach((t) => {
        lines.push(`### ${t.groundNumber}: ${t.legalIssueTitle || 'Legal Ground'}`);
        lines.push(`- **Origin:** ${t.sourcePassage.documentName} (Page ${t.sourcePassage.pageNumber || 'Unresolved'}, ${t.sourcePassage.extractionMethod})`);
        lines.push(`- **Fact Assertion (${t.factAssertion.classification}):** ${t.factAssertion.statement}`);
        lines.push(`- **Statutory Provision:** ${t.statutoryProvision}`);
        if (t.precedent) {
          lines.push(`- **Precedent Authority:** ${t.precedent.caseTitle} [${t.precedent.citation}]`);
          if (t.precedent.signals) {
            lines.push(`  - Retrieval Signals: RRF Score ${t.precedent.signals.rrfScore?.toFixed(4)}, TF-IDF #${t.precedent.signals.tfidfRank || 'N/A'}, BM25 #${t.precedent.signals.bm25Rank || 'N/A'}`);
          }
        }
        if (t.judgmentPassage) {
          lines.push(`- **Judgment Passage:** ${t.judgmentPassage.isDirectQuote ? `Direct Quote (${t.judgmentPassage.pinpointCitation})` : 'Editorial Paraphrase'} — ${t.judgmentPassage.verbatimQuote || t.judgmentPassage.editorialParaphrase}`);
        }
        if (t.confidenceAssessment.isOcrUncertain && t.confidenceAssessment.ocrReliabilityCaveat) {
          lines.push(`- **⚠️ OCR Reliability Caveat:** ${t.confidenceAssessment.ocrReliabilityCaveat}`);
        }
        lines.push('');
      });
    }
    if (researchNotes.trim()) {
      lines.push('## 7. Counsel Research Notes');
      lines.push(researchNotes);
      lines.push('');
    }
    lines.push('---');
    lines.push('*Legal Research Output Only. Subject to independent verification by counsel prior to filing.*');
    return lines.join('\n');
  };

  const handleDownload = (ext: 'md' | 'txt') => {
    if (!analysis) return;
    const content = buildExportMarkdown(analysis);
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeSlug = analysis.caseTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 50);
    a.download = `${safeSlug || 'legal-dossier'}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return <LoadingSpinner message="Assembling legal research dossier and verifying statutory citations..." />;
  }

  if (error || !analysis) {
    return (
      <div className="bg-white rounded border border-gold-500/30 p-12 text-center space-y-4 shadow-judicial">
        <AlertTriangle className="w-12 h-12 text-burgundy-900 mx-auto" />
        <h3 className="text-lg font-serif font-bold text-navy-900">Research Dossier Not Found</h3>
        <p className="text-xs text-charcoal-500 max-w-sm mx-auto">
          {error || 'Unable to locate this analysis record.'}
        </p>
        <Link
          to="/dashboard/history"
          className="inline-flex items-center gap-2 px-4 py-2 bg-navy-900 text-gold-300 rounded text-xs font-serif font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Case History</span>
        </Link>
      </div>
    );
  }

  const tabs: Array<{ key: TabKey; label: string; icon: any; count?: number }> = [
    { key: 'overview', label: 'Case & Chronology', icon: Clock },
    ...(analysis.documentMetadata
      ? [
          {
            key: 'document' as TabKey,
            label: 'Document & OCR',
            icon: FileText,
            count: analysis.documentMetadata.pageCount
          }
        ]
      : []),
    { key: 'law', label: 'Applicable Legislation', icon: FileCode2 },
    { key: 'issues', label: 'Questions of Law', icon: Scale, count: analysis.legalIssues?.length || 0 },
    { key: 'precedents', label: 'Authorities & Matches', icon: BookOpen, count: analysis.similarCases?.length || 0 },
    { key: 'arguments', label: 'Submissions & Rebuttals', icon: ScrollText, count: analysis.legalArguments?.length || 0 },
    { key: 'evidence', label: 'Evidence Trace', icon: Layers, count: analysis.evidenceTraceGraph?.length || 0 },
    { key: 'treatment', label: 'Outcome & Judicial Treatment', icon: Gavel },
    { key: 'notes', label: 'Notes & Statutes', icon: StickyNote }
  ];

  return (
    <div className="space-y-6 bg-ivory-100">
      {/* Persistence Mode Notice (only when DB inactive) */}
      {analysis.persistenceMode === 'in_memory_fallback' && (
        <div className="bg-gold-100 border border-gold-500 rounded p-3 text-xs text-charcoal-900 flex items-start gap-2 no-print">
          <AlertTriangle className="w-4 h-4 text-burgundy-900 shrink-0 mt-0.5" />
          <span>
            <strong>Session Storage Notice:</strong> External MongoDB persistence is currently inactive; this dossier, edited drafts, and bookmarks are active for the current server session. Export to Markdown or Print for permanent retention.
          </span>
        </div>
      )}

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-ivory-300 no-print">
        <Link
          to="/dashboard/history"
          className="text-xs font-serif font-semibold text-charcoal-600 hover:text-navy-900 flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4 text-gold-600" />
          <span>Case History</span>
        </Link>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => handleDownload('md')}
            className="px-3 py-1.5 rounded border border-ivory-400 bg-white hover:border-gold-500 text-xs font-medium text-navy-900 inline-flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-gold-700" />
            <span>Export .MD</span>
          </button>
          <button
            type="button"
            onClick={() => handleDownload('txt')}
            className="px-3 py-1.5 rounded border border-ivory-400 bg-white hover:border-gold-500 text-xs font-medium text-navy-900 inline-flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-gold-700" />
            <span>Export .TXT</span>
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3.5 py-1.5 rounded bg-navy-900 hover:bg-navy-800 text-xs font-serif font-semibold text-gold-300 inline-flex items-center gap-1.5"
          >
            <Printer className="w-3.5 h-3.5 text-gold-400" />
            <span>Print Dossier</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="bg-navy-900 text-gold-200 border border-gold-500/40 rounded px-4 py-2.5 text-xs flex items-center gap-2 no-print">
          <Check className="w-4 h-4 text-gold-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Header Dossier Card */}
      <div className="parchment-card rounded p-6 sm:p-7 space-y-4">
        <div className="hidden print:block text-center border-b pb-3 mb-3">
          <h2 className="text-lg font-serif font-bold uppercase tracking-widest text-navy-950">
            IN THE {analysis.court.toUpperCase()}
          </h2>
          <p className="text-xs font-serif italic text-charcoal-600">
            Legal Research &amp; Draft Submissions Dossier
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-serif font-bold px-3 py-1 rounded bg-navy-950 text-gold-300 border border-gold-500/30">
              {analysis.court}
            </span>
            <span className="font-serif font-semibold px-2.5 py-1 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-200">
              {analysis.category}
            </span>
          </div>

          <span className="text-[11px] font-sans text-charcoal-500">
            Prepared{' '}
            {new Date(analysis.createdAt).toLocaleDateString('en-IN', {
              day: 'numeric',
              month: 'long',
              year: 'numeric'
            })}
          </span>
        </div>

        <div className="space-y-2">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-serif font-bold text-navy-900 leading-snug">
            {analysis.caseTitle}
          </h1>
          <div className="text-xs font-sans text-charcoal-700 bg-ivory-50 p-3.5 rounded border border-ivory-200 leading-relaxed max-h-36 overflow-y-auto">
            <strong className="text-navy-950 font-serif block mb-1">Submitted Fact Narrative:</strong>
            {analysis.inputTextSnippet}
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 pb-1 no-print">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded text-xs font-serif font-semibold border transition-colors ${
                isActive
                  ? 'bg-navy-900 text-gold-300 border-navy-900 shadow-sm'
                  : 'bg-white text-charcoal-700 border-ivory-300 hover:border-gold-500 hover:text-navy-900'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-gold-400' : 'text-gold-700'}`} />
              <span>
                {tab.label}
                {typeof tab.count === 'number' ? ` (${tab.count})` : ''}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Section View (Screen) */}
      <div className="space-y-6 print:hidden">
        {activeTab === 'overview' && (
          <CaseFactsSynthesisView understanding={analysis.caseUnderstanding} />
        )}

        {activeTab === 'document' && (
          <DocumentIntelligenceView
            documentMetadata={analysis.documentMetadata}
            extractedTextSnippet={analysis.inputTextSnippet}
          />
        )}

        {activeTab === 'law' && <ApplicableLawView law={analysis.applicableLaw} />}

        {activeTab === 'issues' && <LegalIssueCard issues={analysis.legalIssues} />}

        {activeTab === 'precedents' && (
          <div className="space-y-4">
            <div className="bg-ivory-50 border border-gold-500/35 p-4 rounded text-xs text-charcoal-700">
              <strong className="font-serif text-navy-900 block mb-1">
                Source Verification, Hybrid Retrieval &amp; Article 141 Relevance Policy
              </strong>
              Precedents are ranked via reciprocal rank fusion (RRF) integrating sparse BM25, TF-IDF lexical matches, and dense legal embeddings. Records verified directly against official court portals carry the <strong>Official Source Verified</strong> badge with authentic e-SCR / SCI links. Expand any precedent to examine the signal breakdown and matched judgment passages.
            </div>
            {!analysis.similarCases || analysis.similarCases.length === 0 ? (
              <div className="p-8 text-center text-xs text-charcoal-500 bg-white rounded border border-ivory-300">
                No sufficiently aligned precedents found in the current corpus.
              </div>
            ) : (
              analysis.similarCases.map((item, idx) => {
                const matchedTrace = analysis.evidenceTraceGraph?.find(
                  (t) =>
                    (t.precedent?.id && item.id && t.precedent.id === item.id) ||
                    (t.precedent?.caseTitle &&
                      item.caseTitle &&
                      t.precedent.caseTitle.toLowerCase() === item.caseTitle.toLowerCase())
                );
                return (
                  <PrecedentCard
                    key={item.id || idx}
                    precedent={item}
                    rank={idx + 1}
                    matchingPassage={matchedTrace?.judgmentPassage}
                    onBookmark={handleBookmarkPrecedent}
                    isBookmarked={Boolean(
                      (item.id && bookmarkedIds.has(item.id)) || bookmarkedIds.has(item.caseTitle)
                    )}
                  />
                );
              })
            )}
          </div>
        )}

        {activeTab === 'arguments' && (
          <LegalArgumentsView
            argumentsList={analysis.legalArguments}
            editedDrafts={analysis.editedDrafts}
            onSaveDraft={handleSaveDraft}
            citationGrounding={analysis.citationGrounding}
            generationMode={analysis.generationMode}
          />
        )}

        {activeTab === 'evidence' && (
          <EvidenceTraceView
            traceNodes={analysis.evidenceTraceGraph}
            documentMetadata={analysis.documentMetadata}
          />
        )}

        {activeTab === 'treatment' && (
          <JudicialTreatmentView assessment={analysis.judicialTreatment} meta={analysis.prediction} />
        )}

        {activeTab === 'notes' && (
          <div className="space-y-6">
            <div className="parchment-card rounded p-5 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-2">
                <div>
                  <h3 className="text-sm font-serif font-bold text-navy-900">
                    Counsel Working Notes &amp; Record Checklist
                  </h3>
                  <p className="text-xs text-charcoal-500">
                    Record missing annexures, hearing dates, and conference instructions here.
                  </p>
                </div>
                <button
                  type="button"
                  disabled={savingNotes}
                  onClick={handleSaveNotes}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-burgundy-900 hover:bg-burgundy-800 text-gold-200 text-xs font-semibold disabled:opacity-60 self-start"
                >
                  {notesSaved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                  <span>{notesSaved ? 'Notes Saved' : savingNotes ? 'Saving...' : 'Save Notes'}</span>
                </button>
              </div>
              <textarea
                rows={7}
                value={researchNotes}
                onChange={(e) => setResearchNotes(e.target.value)}
                placeholder="Enter chamber notes, certified-copy verification reminders, or oral submission points..."
                className="w-full p-3.5 rounded bg-ivory-50 border border-ivory-300 text-xs text-charcoal-900 leading-relaxed focus:outline-none focus:border-navy-900"
              />
            </div>

            <EntityBadgesView entities={analysis.extractedEntities} />
          </div>
        )}
      </div>

      {/* Consolidated Print-Only Dossier View */}
      <div className="hidden print:block space-y-8">
        {analysis.documentMetadata && (
          <DocumentIntelligenceView
            documentMetadata={analysis.documentMetadata}
            extractedTextSnippet={analysis.inputTextSnippet}
          />
        )}
        <CaseFactsSynthesisView understanding={analysis.caseUnderstanding} />
        <ApplicableLawView law={analysis.applicableLaw} />
        <LegalIssueCard issues={analysis.legalIssues} />
        <EvidenceTraceView traceNodes={analysis.evidenceTraceGraph} documentMetadata={analysis.documentMetadata} />
        <LegalArgumentsView
          argumentsList={analysis.legalArguments}
          editedDrafts={analysis.editedDrafts}
          citationGrounding={analysis.citationGrounding}
          generationMode={analysis.generationMode}
        />
        <JudicialTreatmentView assessment={analysis.judicialTreatment} meta={analysis.prediction} />
      </div>

      {/* Bottom Legal Disclaimer */}
      <div className="bg-white border border-gold-500/35 rounded p-4 text-xs text-charcoal-600 parchment-card">
        <div className="flex items-center gap-1.5 text-navy-950 font-serif font-semibold mb-1">
          <Scale className="w-3.5 h-3.5 text-gold-700" />
          <span>Professional Verification Notice</span>
        </div>
        <p className="leading-relaxed text-[11px]">
          This research dossier and its draft submissions are prepared to assist structured legal research. Counsel must verify all statutory amendments, local High Court Rules, and primary judgment copies prior to court filing.
        </p>
      </div>
    </div>
  );
};
