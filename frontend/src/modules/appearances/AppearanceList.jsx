import React, { useMemo, useState } from 'react';
import { Layers, Search, X } from 'lucide-react';
import AppearanceCard from './AppearanceCard';

export default function AppearanceList({ appearances, onDeleteAppearance }) {
  const [filter, setFilter] = useState('ALL');
  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('confidence'); // 'confidence' | 'recent' | 'title'

  const nonRejected = useMemo(
    () => appearances.filter((item) => item.identity_status !== 'REJECTED'),
    [appearances]
  );

  const counts = useMemo(
    () => ({
      ALL: nonRejected.length,
      VERIFIED: nonRejected.filter((i) => i.identity_status === 'VERIFIED').length,
      LIKELY_MATCH: nonRejected.filter((i) => i.identity_status === 'LIKELY_MATCH').length,
      NEEDS_REVIEW: nonRejected.filter((i) => i.identity_status === 'NEEDS_REVIEW').length,
    }),
    [nonRejected]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = nonRejected.filter((item) => {
      if (filter !== 'ALL' && item.identity_status !== filter) return false;
      if (q) {
        const hay = `${item.title || ''} ${item.publisher || ''} ${item.analysis?.summary || ''} ${item.appearance_type || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    return [...list].sort((a, b) => {
      if (sortBy === 'recent') {
        const da = a.published_at ? new Date(a.published_at).getTime() : 0;
        const db = b.published_at ? new Date(b.published_at).getTime() : 0;
        return db - da;
      }
      if (sortBy === 'title') {
        return (a.title || '').localeCompare(b.title || '');
      }
      return (b.confidence_score || 0) - (a.confidence_score || 0);
    });
  }, [nonRejected, filter, query, sortBy]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/80 p-3.5 rounded-2xl border border-slate-200">
        <div className="flex flex-wrap gap-2">
          {['ALL', 'VERIFIED', 'LIKELY_MATCH', 'NEEDS_REVIEW'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide border inline-flex items-center gap-1.5 transition-all ${
                filter === f
                  ? 'bg-blue-600 border-blue-600 text-white shadow-xs'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span>{f.replace('_', ' ')}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  filter === f ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {counts[f]}
              </span>
            </button>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search titles, summaries..."
              className="pl-8 pr-7 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 w-full sm:w-56"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                aria-label="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="text-xs font-medium bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-blue-500"
            aria-label="Sort appearances"
          >
            <option value="confidence">Sort: Highest Confidence</option>
            <option value="recent">Sort: Most Recent</option>
            <option value="title">Sort: Title (A–Z)</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs">
          <Layers size={36} className="mx-auto mb-3 text-slate-400 opacity-50" />
          <p className="text-sm font-medium text-slate-700">No appearances match the current filters.</p>
          <p className="text-xs text-slate-500 mt-1">Try resetting the filter pills or search keywords.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((item) => (
            <AppearanceCard key={item.id} item={item} onDelete={onDeleteAppearance} />
          ))}
        </div>
      )}
    </div>
  );
}
