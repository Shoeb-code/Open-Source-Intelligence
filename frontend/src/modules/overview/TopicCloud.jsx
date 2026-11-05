import React from 'react';
import { TrendingUp } from 'lucide-react';

export default function TopicCloud({ topics }) {
  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
      <h4 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <TrendingUp size={16} className="text-cyan-400" />
        <span>Recurring Topics & Themes</span>
      </h4>
      <div className="flex flex-wrap gap-2">
        {topics && topics.length > 0 ? (
          topics.map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700 text-slate-300 hover:border-cyan-500/50 transition-colors"
            >
              <span>{t.topic}</span>
              <span className="text-cyan-400 font-semibold text-[11px]">{t.count}</span>
            </span>
          ))
        ) : (
          <p className="text-xs text-slate-500">Topics will appear here after discovery.</p>
        )}
      </div>
    </div>
  );
}
