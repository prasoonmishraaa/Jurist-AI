import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  Search,
  Trash2,
  ArrowRight,
  Scale,
  PlusCircle,
  Clock,
  BookOpen,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { CaseAnalysis } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const CaseHistoryPage: React.FC = () => {
  const [analyses, setAnalyses] = useState<CaseAnalysis[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [persistenceMode, setPersistenceMode] = useState<string>('mongodb');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const [res, healthRes] = await Promise.allSettled([
        api.getAnalyses({ page, limit: 8, search, category }),
        api.getHealth()
      ]);
      if (res.status === 'fulfilled') {
        setAnalyses(res.value.data || []);
        setTotalPages(res.value.pagination?.totalPages || 1);
      }
      if (healthRes.status === 'fulfilled' && healthRes.value?.data?.persistenceMode) {
        setPersistenceMode(healthRes.value.data.persistenceMode);
      }
    } catch (err) {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, category]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this case analysis dossier?')) return;
    try {
      await api.deleteAnalysis(id);
      setAnalyses(analyses.filter((a) => (a.id || a._id) !== id));
    } catch (err) {
      alert('Failed to delete analysis record.');
    }
  };

  return (
    <div className="space-y-6 bg-ivory-100">
      {persistenceMode === 'in_memory_fallback' && (
        <div className="bg-gold-100 border border-gold-500 rounded p-3 text-xs text-charcoal-900 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-burgundy-900 shrink-0 mt-0.5" />
          <span>
            <strong>Session Storage Active:</strong> External MongoDB Atlas persistence is currently inactive. Archived dossiers are maintained for the active server session only. Export important dossiers to Markdown or Print before server restart.
          </span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
            <History className="w-3.5 h-3.5 text-gold-600" />
            <span>Litigation Brief Archive</span>
          </div>
          <h1 className="text-2xl font-serif font-bold text-navy-900">
            Case Analysis & Submissions History
          </h1>
          <p className="text-xs text-charcoal-600">
            Review past case evaluations, formal court grounds, and retrieved Article 141 precedent dossiers.
          </p>
        </div>

        <Link
          to="/dashboard/new-analysis"
          className="inline-flex items-center gap-2 px-4 py-2 bg-navy-900 hover:bg-navy-850 text-gold-300 rounded text-xs font-serif font-semibold transition-colors shadow-sm self-start sm:self-auto border border-gold-500/30"
        >
          <PlusCircle className="w-4 h-4 text-gold-400" />
          <span>New Case Submission</span>
        </Link>
      </div>

      {/* Search & Category Filter */}
      <div className="bg-white rounded border border-gold-500/30 p-4 shadow-sm flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by case title or factual keywords..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 transition-all font-sans"
          />
        </form>

        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded text-charcoal-700 focus:outline-none focus:border-gold-500 transition-all font-sans"
        >
          <option value="All">All Legal Domains</option>
          <option value="Constitutional Law">Constitutional Law</option>
          <option value="Criminal Law">Criminal Law</option>
          <option value="Corporate & Commercial Law">Corporate & Commercial</option>
          <option value="Cyber & Information Technology Law">Cyber & IT Law</option>
          <option value="Banking & Negotiable Instruments">Banking & NI Act</option>
          <option value="Family Law">Family Law</option>
          <option value="Labour & Service Law">Labour & Service Law</option>
          <option value="Civil Law">Civil Law</option>
        </select>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Retrieving litigation briefs from chamber archive..." />
      ) : analyses.length === 0 ? (
        <div className="bg-white rounded border border-gold-500/20 p-12 text-center text-xs text-charcoal-500 space-y-2">
          <Scale className="w-10 h-10 text-gold-400/50 mx-auto" />
          <h3 className="font-serif font-bold text-navy-900 text-sm">No analysis history found</h3>
          <p>Prepare your first legal case analysis to populate your chamber archive.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {analyses.map((item) => (
            <div
              key={item.id || item._id}
              className="bg-white rounded border border-gold-500/30 p-5 shadow-sm hover:border-gold-500 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 parchment-card"
            >
              <div className="space-y-1.5 max-w-2xl">
                <div className="flex items-center gap-2">
                  <span className="text-[10.5px] font-serif font-bold px-2.5 py-0.5 rounded bg-ivory-200 text-navy-950 border border-gold-500/20">
                    {item.court}
                  </span>
                  <span className="text-[10.5px] font-sans text-burgundy-900 font-semibold px-2 py-0.5 rounded bg-burgundy-50 border border-burgundy-200">
                    {item.category}
                  </span>
                  <span className="text-[10.5px] font-sans text-charcoal-400">
                    {new Date(item.createdAt).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric'
                    })}
                  </span>
                </div>

                <h3 className="text-base font-serif font-bold text-navy-900">
                  {item.caseTitle}
                </h3>

                <p className="text-xs text-charcoal-600 line-clamp-2 leading-relaxed font-sans">
                  {item.inputTextSnippet}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
                <Link
                  to={`/dashboard/analysis/${item.id || item._id}`}
                  className="px-3.5 py-2 rounded bg-navy-900 hover:bg-navy-850 text-gold-300 border border-gold-500/30 text-xs font-serif font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <span>Inspect Dossier</span>
                  <ArrowRight className="w-3.5 h-3.5 text-gold-400" />
                </Link>

                <button
                  onClick={() => handleDelete(item.id || item._id || '')}
                  className="p-2 rounded hover:bg-burgundy-50 text-charcoal-400 hover:text-burgundy-800 transition-colors"
                  title="Purge dossier from chamber record"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1.5 rounded border border-gold-500/30 bg-white text-xs font-serif font-semibold text-charcoal-700 disabled:opacity-40 hover:bg-navy-900 hover:text-gold-300 transition-colors"
              >
                Previous
              </button>
              <span className="text-xs font-serif text-charcoal-600 px-3">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1.5 rounded border border-gold-500/30 bg-white text-xs font-serif font-semibold text-charcoal-700 disabled:opacity-40 hover:bg-navy-900 hover:text-gold-300 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
