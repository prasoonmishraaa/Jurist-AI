import React, { useEffect, useState } from 'react';
import {
  Bookmark,
  ExternalLink,
  Trash2,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Save,
  Check
} from 'lucide-react';
import { api } from '../services/api';
import { SavedCase } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const SavedJudgmentsPage: React.FC = () => {
  const [savedCases, setSavedCases] = useState<SavedCase[]>([]);
  const [notesDraft, setNotesDraft] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSaved = async () => {
    setIsLoading(true);
    try {
      const data = await api.getSavedCases();
      const list = data || [];
      setSavedCases(list);
      const initialNotes: Record<string, string> = {};
      list.forEach((s) => {
        const key = s.id || s._id || '';
        initialNotes[key] = s.notes || '';
      });
      setNotesDraft(initialNotes);
    } catch {
      // graceful fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSaved();
  }, []);

  const handleSaveNotes = async (id: string) => {
    try {
      setSavingId(id);
      const updated = await api.updateSavedCaseNotes(id, notesDraft[id] || '');
      setSavedCases((prev) => prev.map((s) => ((s.id || s._id) === id ? updated : s)));
      setSavedId(id);
      setTimeout(() => setSavedId(null), 2000);
    } finally {
      setSavingId(null);
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await api.deleteSavedCase(id);
      setSavedCases((prev) => prev.filter((s) => (s.id || s._id) !== id));
    } catch {
      // ignore
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading bookmarked judicial authorities..." />;
  }

  return (
    <div className="space-y-6 bg-ivory-100">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
          <Bookmark className="w-3.5 h-3.5 text-gold-600" />
          <span>Chamber Bookmarks</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-navy-900">
          Saved Authorities &amp; Research Notes
        </h1>
        <p className="text-xs text-charcoal-600">
          Manage bookmarked Supreme Court and High Court rulings along with verification status and chamber conference notes.
        </p>
      </div>

      {savedCases.length === 0 ? (
        <div className="bg-white rounded border border-gold-500/25 p-12 text-center space-y-3 parchment-card">
          <BookOpen className="w-10 h-10 text-gold-500/60 mx-auto" />
          <h3 className="font-serif font-bold text-navy-900 text-sm">No saved authorities yet</h3>
          <p className="text-xs text-charcoal-500 max-w-sm mx-auto">
            Bookmark authorities from your case analysis or browse the Precedent Corpus to build your quick-reference shelf.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {savedCases.map((saved) => {
            const key = saved.id || saved._id || '';
            return (
              <div
                key={key}
                className="parchment-card rounded p-5 space-y-3.5 flex flex-col justify-between hover:border-gold-500 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[10.5px] font-serif font-bold px-2.5 py-0.5 rounded bg-ivory-200 text-navy-950 border border-gold-500/20">
                      {saved.court}
                    </span>

                    {saved.officialSourceVerified ? (
                      <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded bg-navy-50 text-navy-900 border border-navy-200">
                        <CheckCircle2 className="w-3 h-3" /> Official Verified
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded bg-burgundy-50 text-burgundy-900 border border-burgundy-200">
                        <AlertTriangle className="w-3 h-3" /> Official source not verified
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-serif font-bold text-navy-900 leading-snug">
                    {saved.caseTitle}
                  </h3>

                  {saved.citation && (
                    <p className="text-xs font-mono font-bold text-burgundy-900 bg-ivory-50 px-2.5 py-1 rounded border border-ivory-300 inline-block">
                      {saved.citation}
                    </p>
                  )}

                  <div className="pt-1 space-y-1.5">
                    <label className="text-[11px] font-serif font-semibold text-charcoal-600 block">
                      Chamber Notes
                    </label>
                    <textarea
                      rows={2}
                      value={notesDraft[key] ?? ''}
                      onChange={(e) =>
                        setNotesDraft((prev) => ({
                          ...prev,
                          [key]: e.target.value
                        }))
                      }
                      placeholder="Add paragraph citation, bench note, or distinguishing facts..."
                      className="w-full p-2.5 rounded bg-ivory-50 border border-ivory-300 text-xs text-charcoal-800 focus:outline-none focus:border-navy-900"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-ivory-200">
                  <div className="flex items-center gap-3">
                    {saved.officialSourceVerified && saved.officialSourceUrl ? (
                      <a
                        href={saved.officialSourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-serif font-semibold text-navy-900 hover:text-burgundy-900 flex items-center gap-1 underline"
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-gold-700" />
                        <span>Official Judgment</span>
                      </a>
                    ) : saved.sourceUrl ? (
                      <a
                        href={saved.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-serif font-semibold text-burgundy-900 hover:text-navy-900 flex items-center gap-1 underline"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>Reference Record</span>
                      </a>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={savingId === key}
                      onClick={() => handleSaveNotes(key)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold bg-navy-900 hover:bg-navy-800 text-gold-300"
                    >
                      {savedId === key ? <Check className="w-3 h-3" /> : <Save className="w-3 h-3" />}
                      <span>{savedId === key ? 'Saved' : 'Save Note'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleRemove(key)}
                      className="p-1.5 rounded hover:bg-burgundy-50 text-charcoal-500 hover:text-burgundy-800 transition-colors"
                      title="Remove bookmark"
                      aria-label="Remove bookmark"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
