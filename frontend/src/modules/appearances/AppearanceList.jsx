import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import AppearanceCard from './AppearanceCard';

export default function AppearanceList({ appearances, onDeleteAppearance }) {
  const [filter, setFilter] = useState('ALL');

  const filtered = appearances.filter((item) => {
    if (filter === 'ALL') return true;
    return item.identity_status === filter;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {['ALL', 'VERIFIED', 'LIKELY_MATCH', 'NEEDS_REVIEW'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide border transition-all ${
              filter === f
                ? 'bg-cyan-500/15 border-cyan-400 text-cyan-400 shadow-sm shadow-cyan-500/20'
                : 'bg-transparent border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200'
            }`}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-xl border border-slate-700/60 bg-slate-900/60">
          <Layers size={36} className="mx-auto mb-3 text-slate-500 opacity-40" />
          <p className="text-sm text-slate-400">No appearances match the selected filter.</p>
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
