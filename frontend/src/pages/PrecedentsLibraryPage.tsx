import React, { useEffect, useState } from 'react';
import { BookOpen, Search, Scale } from 'lucide-react';
import { api } from '../services/api';
import { Precedent } from '../types';
import { PrecedentCard } from '../components/analysis/PrecedentCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { SpeechToTextButton } from '../components/common/SpeechToTextButton';
import { useAuth } from '../contexts/AuthContext';

export const PrecedentsLibraryPage: React.FC = () => {
  const { user } = useAuth();
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [court, setCourt] = useState('All');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchPrecedents = async () => {
    setIsLoading(true);
    try {
      const res = await api.getPrecedents({ page, limit: 8, search, category, court });
      setPrecedents(res.data || []);
      setTotalPages(res.pagination?.totalPages || 1);
      if (user) {
        const saved = await api.getSavedCases().catch(() => []);
        setBookmarkedIds(
          new Set((saved || []).map((s: any) => s.precedentCode || s.caseTitle).filter(Boolean))
        );
      }
    } catch {
      // graceful fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPrecedents();
  }, [page, category, court]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchPrecedents();
  };

  const handleBookmark = async (precedent: Precedent) => {
    if (!user) return;
    try {
      await api.saveCase({
        precedentId: precedent.id,
        precedentCode: precedent.id,
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
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6 bg-ivory-100">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
          <BookOpen className="w-3.5 h-3.5 text-gold-600" />
          <span>Verified Judgment Index</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-navy-900">
          Landmark Indian Precedent Corpus
        </h1>
        <p className="text-xs text-charcoal-600">
          Explore Supreme Court and High Court authorities with verified e-SCR / SCI PDF links, transparent source status badges, and Article 141 scope summaries.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded border border-gold-500/35 p-4 parchment-card flex flex-col lg:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search case title, citation (e.g. 2025 5 SCC 799), or statutory provision..."
              className="w-full pl-9 pr-10 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-navy-900 font-sans"
            />
            <div className="absolute right-1.5 top-1.5">
              <SpeechToTextButton
                onTranscript={(transcript) => {
                  setSearch((prev) => (prev ? `${prev} ${transcript}` : transcript));
                }}
                size="sm"
                title="Dictate search query using microphone"
              />
            </div>
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded bg-navy-900 hover:bg-navy-800 text-gold-300 text-xs font-serif font-semibold shrink-0"
          >
            Search
          </button>
        </form>

        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded text-charcoal-700 focus:outline-none focus:border-navy-900 font-sans"
        >
          <option value="All">All Practice Areas</option>
          <option value="Constitutional Law">Constitutional Law</option>
          <option value="Criminal Law">Criminal Law</option>
          <option value="Corporate & Commercial Law">Corporate &amp; Commercial</option>
          <option value="Cyber & Information Technology Law">Cyber &amp; IT Law</option>
          <option value="Banking & Negotiable Instruments">Banking &amp; NI Act</option>
          <option value="Family Law">Family Law</option>
          <option value="Labour & Service Law">Labour &amp; Service Law</option>
          <option value="Civil Law">Civil Law</option>
        </select>

        <select
          value={court}
          onChange={(e) => {
            setCourt(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded text-charcoal-700 focus:outline-none focus:border-navy-900 font-sans"
        >
          <option value="All">All Courts</option>
          <option value="Supreme Court of India">Supreme Court of India</option>
          <option value="High Court of Delhi">High Court of Delhi</option>
          <option value="High Court of Bombay">High Court of Bombay</option>
          <option value="High Court of Judicature at Allahabad">High Court of Allahabad</option>
        </select>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading verified Indian court judgments..." />
      ) : precedents.length === 0 ? (
        <div className="bg-white rounded border border-gold-500/25 p-12 text-center text-xs text-charcoal-500 space-y-2 parchment-card">
          <Scale className="w-10 h-10 text-gold-500/60 mx-auto" />
          <h3 className="font-serif font-bold text-navy-900 text-sm">No matching judgments</h3>
          <p>Broaden your search keywords or reset category/court filters.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {precedents.map((precedent) => (
              <PrecedentCard
                key={precedent.id || precedent._id}
                precedent={precedent}
                onBookmark={user ? handleBookmark : undefined}
                isBookmarked={Boolean(
                  (precedent.id && bookmarkedIds.has(precedent.id)) ||
                    bookmarkedIds.has(precedent.caseTitle)
                )}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1.5 rounded border border-gold-500/35 bg-white text-xs font-serif font-semibold text-charcoal-700 disabled:opacity-40 hover:bg-navy-900 hover:text-gold-300 transition-colors"
              >
                Previous
              </button>
              <span className="text-xs font-serif text-charcoal-600 px-3">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1.5 rounded border border-gold-500/35 bg-white text-xs font-serif font-semibold text-charcoal-700 disabled:opacity-40 hover:bg-navy-900 hover:text-gold-300 transition-colors"
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
