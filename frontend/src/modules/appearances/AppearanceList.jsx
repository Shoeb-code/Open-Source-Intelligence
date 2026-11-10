import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import AppearanceCard from './AppearanceCard';

export default function AppearanceList({ appearances, onDeleteAppearance }) {
  const [filter, setFilter] = useState('ALL');

  const filtered = appearances.filter((item) => {
    if (filter === 'ALL') return item.identity_status !== 'REJECTED';
    return item.identity_status === filter;
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {['ALL', 'VERIFIED', 'LIKELY_MATCH', 'NEEDS_REVIEW'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide border transition-all ${
              filter === f
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-xl border border-slate-200 shadow-xs">
          <Layers size={36} className="mx-auto mb-3 text-slate-400 opacity-50" />
          <p className="text-sm text-slate-500">No appearances match the selected filter.</p>
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
