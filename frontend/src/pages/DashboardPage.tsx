import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PlusCircle,
  FileText,
  Bookmark,
  BookOpen,
  ArrowRight,
  Scale,
  Clock,
  ExternalLink,
  AlertTriangle,
  Layers,
  ShieldCheck,
  CheckCircle2,
  Database
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';
import { CaseAnalysis, SavedCase, CorpusStatistics } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState<CaseAnalysis[]>([]);
  const [savedCases, setSavedCases] = useState<SavedCase[]>([]);
  const [corpusStats, setCorpusStats] = useState<CorpusStatistics | null>(null);
  const [corpusLoading, setCorpusLoading] = useState<boolean>(true);
  const [corpusError, setCorpusError] = useState<string | null>(null);
  const [persistenceMode, setPersistenceMode] = useState<string>('mongodb');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [analysisRes, savedRes, healthRes, statsRes] = await Promise.all([
          api.getAnalyses({ limit: 6 }).catch(() => ({ data: [] })),
          api.getSavedCases().catch(() => []),
          api.getHealth().catch(() => null),
          api.getCorpusStats().catch(() => null)
        ]);
        setAnalyses(analysisRes.data || []);
        setSavedCases(savedRes || []);

        const resolvedStats = statsRes || healthRes?.data?.corpusStats;
        if (resolvedStats) {
          setCorpusStats(resolvedStats);
          setCorpusError(null);
        } else if (healthRes?.data?.verifiedPrecedentCount) {
          setCorpusStats({
            totalJudgments: healthRes.data.verifiedPrecedentCount,
            indexedPassages: healthRes.data.indexedPassagesCount || 771,
            landmarkJudgments: healthRes.data.landmarkPrecedentCount || 27,
            officialVerifiedLandmarks: 10,
            secondaryReferences: 17,
            openIndiaLawJudgments: 149,
            databaseSyncedRecords: healthRes.data.databaseSyncedPrecedentCount || 27,
            retrievalEngine: 'Hybrid RRF (TF-IDF + BM25 + Semantic)',
            manifestVersion: 'v1.4.0-unified',
            activeModalities: ['tfidf', 'bm25', 'semantic'],
            semanticModel: 'BAAI/bge-small-en-v1.5',
            isMlServiceConnected: Boolean(healthRes.data.mlService?.pythonService?.status === 'healthy')
          });
        } else {
          setCorpusError('Live corpus metrics offline; showing baseline corpus register.');
        }

        if (healthRes?.data?.persistenceMode) {
          setPersistenceMode(healthRes.data.persistenceMode);
        }
      } catch (err: any) {
        setCorpusError(err.message || 'Unable to load real-time corpus metrics');
      } finally {
        setIsLoading(false);
        setCorpusLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (isLoading) {
    return <LoadingSpinner message="Loading workspace dossiers and authority registers..." />;
  }

  return (
    <div className="space-y-7 bg-ivory-100">
      {persistenceMode === 'in_memory_fallback' && (
        <div className="bg-gold-100 border border-gold-500 rounded p-3 text-xs text-charcoal-900 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-burgundy-900 shrink-0 mt-0.5" />
          <span>
            <strong>Session Storage Active:</strong> Persistent MongoDB is not configured on this instance. Export important dossiers to Markdown/PDF before ending your session.
          </span>
        </div>
      )}

      {/* Chamber Banner */}
      <div className="bg-navy-950 rounded border border-gold-500/35 p-6 sm:p-8 text-white shadow-judicial flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 text-[11px] text-gold-400 font-serif font-semibold uppercase tracking-widest bg-navy-900 px-3 py-1 rounded border border-gold-500/30">
            <Scale className="w-3.5 h-3.5 text-gold-400" />
            <span>Litigation Research &amp; Drafting Chamber</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white tracking-wide">
            Workspace of {user?.name || 'Legal Counsel'}
          </h1>
          <p className="text-xs sm:text-sm text-charcoal-300 max-w-xl font-sans font-light leading-relaxed">
            Examine fact chronologies, pre-/post-1 July 2024 statutory frameworks, Supreme Court ratios under Article 141, and editable submissions with adversarial rebuttals.
          </p>
        </div>

        <Link
          to="/dashboard/new-analysis"
          className="px-5 py-3 rounded bg-burgundy-900 hover:bg-burgundy-800 text-gold-200 font-serif font-semibold text-xs tracking-wider border border-gold-500/40 transition-colors shadow-judicial flex items-center gap-2 shrink-0"
        >
          <PlusCircle className="w-4 h-4 text-gold-400" />
          <span>New Case Analysis</span>
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded border border-gold-500/35 p-5 parchment-card space-y-1">
          <div className="flex items-center justify-between text-charcoal-500 mb-2">
            <span className="text-[11px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Research Dossiers
            </span>
            <FileText className="w-4 h-4 text-burgundy-900" />
          </div>
          <div className="text-3xl font-serif font-bold text-navy-900">{analyses.length}</div>
          <span className="text-[11px] text-charcoal-500">Prepared case evaluations</span>
        </div>

        <div className="bg-white rounded border border-gold-500/35 p-5 parchment-card space-y-1">
          <div className="flex items-center justify-between text-charcoal-500 mb-2">
            <span className="text-[11px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Saved Authorities
            </span>
            <Bookmark className="w-4 h-4 text-gold-600" />
          </div>
          <div className="text-3xl font-serif font-bold text-navy-900">{savedCases.length}</div>
          <span className="text-[11px] text-charcoal-500">Bookmarked rulings &amp; notes</span>
        </div>

        <div className="bg-white rounded border border-gold-500/35 p-5 parchment-card space-y-1">
          <div className="flex items-center justify-between text-charcoal-500 mb-2">
            <span className="text-[11px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Retrieval Corpus
            </span>
            <BookOpen className="w-4 h-4 text-navy-800" />
          </div>
          {corpusLoading ? (
            <div className="h-9 w-24 bg-ivory-200 animate-pulse rounded my-0.5" />
          ) : (
            <div className="text-3xl font-serif font-bold text-navy-900">
              {corpusStats?.totalJudgments ?? 176} Judgments
            </div>
          )}
          <span className="text-[11px] text-charcoal-500">
            27 Landmark + 149 Open India Law
          </span>
        </div>

        <div className="bg-white rounded border border-gold-500/35 p-5 parchment-card space-y-1">
          <div className="flex items-center justify-between text-charcoal-500 mb-2">
            <span className="text-[11px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Indexed Passages
            </span>
            <Layers className="w-4 h-4 text-gold-700" />
          </div>
          {corpusLoading ? (
            <div className="h-9 w-24 bg-ivory-200 animate-pulse rounded my-0.5" />
          ) : (
            <div className="text-3xl font-serif font-bold text-navy-900">
              {corpusStats?.indexedPassages ?? 771} Passages
            </div>
          )}
          <span className="text-[11px] text-charcoal-500">
            Dense vector &amp; BM25 semantic index
          </span>
        </div>
      </div>

      {/* Corpus Provenance & Dual-Store Architecture Breakdown */}
      <div className="bg-white rounded border border-gold-500/35 p-4 parchment-card space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-ivory-200 pb-2.5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-burgundy-900" />
            <h3 className="text-xs font-serif font-bold text-navy-900 uppercase tracking-wider">
              Precedent Corpus Verification &amp; Dual-Store Architecture
            </h3>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
            <span className="px-2 py-0.5 rounded bg-ivory-100 text-charcoal-600 border border-ivory-300">
              Manifest: {corpusStats?.manifestVersion || 'v1.4.0-unified'}
            </span>
            <span
              className={`px-2 py-0.5 rounded font-semibold border ${
                corpusStats?.isMlServiceConnected
                  ? 'bg-green-50 text-green-800 border-green-300'
                  : 'bg-gold-50 text-gold-900 border-gold-400'
              }`}
            >
              {corpusStats?.isMlServiceConnected
                ? '● ML Hybrid Retrieval Active'
                : '○ Standalone Registry Mode'}
            </span>
          </div>
        </div>

        {corpusError && (
          <div className="p-2.5 bg-burgundy-50 border border-burgundy-200 rounded text-xs text-burgundy-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-burgundy-800" />
            <span>{corpusError}</span>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-0.5">
          <div className="p-3 bg-ivory-50 rounded border border-ivory-200 space-y-1">
            <span className="text-[10px] uppercase font-serif tracking-wider text-charcoal-500 block">
              Hybrid Retrieval Corpus
            </span>
            <span className="text-xl font-serif font-bold text-navy-900 block">
              {corpusStats?.totalJudgments ?? 176}
            </span>
            <span className="text-[11px] text-charcoal-600 block">
              176 unique judgments (27 landmark + 149 Open India Law)
            </span>
          </div>

          <div className="p-3 bg-ivory-50 rounded border border-ivory-200 space-y-1">
            <span className="text-[10px] uppercase font-serif tracking-wider text-charcoal-500 block">
              Official Source Verified
            </span>
            <span className="text-xl font-serif font-bold text-green-800 block">
              {corpusStats?.officialVerifiedLandmarks ?? 10}
            </span>
            <span className="text-[11px] text-charcoal-600 block">
              10 landmark judgments with verified e-SCR / SCI links
            </span>
          </div>

          <div className="p-3 bg-ivory-50 rounded border border-ivory-200 space-y-1">
            <span className="text-[10px] uppercase font-serif tracking-wider text-charcoal-500 block">
              Secondary References
            </span>
            <span className="text-xl font-serif font-bold text-burgundy-900 block">
              {corpusStats?.secondaryReferences ?? 17}
            </span>
            <span className="text-[11px] text-charcoal-600 block">
              17 landmark rulings verified against secondary law reports
            </span>
          </div>

          <div className="p-3 bg-ivory-50 rounded border border-ivory-200 space-y-1">
            <span className="text-[10px] uppercase font-serif tracking-wider text-charcoal-500 block">
              Database Synced Records
            </span>
            <span className="text-xl font-serif font-bold text-navy-900 block">
              {corpusStats?.databaseSyncedRecords ?? 27}
            </span>
            <span className="text-[11px] text-charcoal-600 block">
              {persistenceMode === 'mongodb' ? 'MongoDB collection' : 'In-memory session store'}
            </span>
          </div>
        </div>

        <div className="bg-ivory-100/70 border border-ivory-300 rounded p-2.5 text-[11px] text-charcoal-700 leading-relaxed font-sans">
          <strong className="text-navy-950 font-serif">Dual-Store Architecture Note: </strong>
          The ML hybrid retrieval corpus searches across <strong>176 unique judgments</strong> and <strong>771 indexed passages</strong> using dense embeddings (BAAI/bge-small-en-v1.5), BM25, and TF-IDF. The application database stores <strong>27 landmark authorities</strong> synchronized for user bookmarks, notes, and dossier linkage.
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-7">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-serif font-bold text-navy-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-burgundy-900" />
              <span>Recent Case Dossiers</span>
            </h2>
            <Link to="/dashboard/history" className="text-xs font-serif font-semibold text-burgundy-900 hover:underline">
              View All History →
            </Link>
          </div>

          {analyses.length === 0 ? (
            <div className="bg-white rounded border border-gold-500/25 p-8 text-center space-y-3 parchment-card">
              <Scale className="w-10 h-10 text-gold-600/60 mx-auto" />
              <h4 className="text-sm font-serif font-semibold text-navy-900">No case analyses yet</h4>
              <p className="text-xs text-charcoal-500 max-w-sm mx-auto">
                Enter factual dispute details or attach a petition/FIR document to compile statutory analysis and draft submissions.
              </p>
              <Link
                to="/dashboard/new-analysis"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-navy-900 text-gold-300 rounded text-xs font-serif font-semibold"
              >
                <PlusCircle className="w-3.5 h-3.5 text-gold-400" />
                <span>Start First Analysis</span>
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {analyses.map((item) => (
                <Link
                  key={item.id || item._id}
                  to={`/dashboard/analysis/${item.id || item._id}`}
                  className="block parchment-card rounded p-4 hover:border-gold-500 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded bg-navy-950 text-gold-300">
                          {item.court}
                        </span>
                        <span className="text-[10.5px] font-medium px-2 py-0.5 rounded bg-ivory-200 text-burgundy-900">
                          {item.category}
                        </span>
                      </div>
                      <h3 className="text-sm font-serif font-bold text-navy-900 truncate pt-0.5">
                        {item.caseTitle}
                      </h3>
                      <p className="text-xs text-charcoal-600 line-clamp-2">{item.inputTextSnippet}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gold-700 shrink-0 mt-1" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Bookmarks Column */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-serif font-bold text-navy-900 flex items-center gap-2">
              <Bookmark className="w-4 h-4 text-gold-600" />
              <span>Saved Authorities</span>
            </h2>
            <Link to="/dashboard/saved" className="text-xs font-serif font-semibold text-burgundy-900 hover:underline">
              Manage →
            </Link>
          </div>

          {savedCases.length === 0 ? (
            <div className="bg-white rounded border border-gold-500/25 p-6 text-center text-xs text-charcoal-500 parchment-card">
              Bookmark judgments from an analysis or the Precedent Library for rapid reference.
            </div>
          ) : (
            <div className="space-y-2.5">
              {savedCases.slice(0, 5).map((s) => (
                <div key={s.id || s._id} className="bg-white border border-gold-500/30 rounded p-3.5 text-xs space-y-1">
                  <h4 className="font-serif font-bold text-navy-900 line-clamp-2">{s.caseTitle}</h4>
                  <p className="font-mono text-[11px] text-burgundy-900">{s.citation}</p>
                  {s.sourceUrl && (
                    <a
                      href={s.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-navy-900 hover:underline pt-0.5"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span>{s.officialSourceVerified ? 'Official Judgment' : 'Reference Record'}</span>
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
