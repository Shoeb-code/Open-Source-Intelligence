import React from 'react';
import { Calendar, ExternalLink } from 'lucide-react';

export default function TimelineView({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="glass-panel p-12 text-center rounded-xl border border-slate-700/60 bg-slate-900/60 max-w-2xl mx-auto">
        <Calendar size={36} className="mx-auto mb-3 text-slate-500 opacity-40" />
        <p className="text-sm text-slate-400">No timeline entries available.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-2 sm:py-4">
      <div className="relative border-l-2 border-slate-700 ml-2.5 sm:ml-4 space-y-5 sm:space-y-6">
        {timeline.map((entry, idx) => (
          <div key={idx} className="relative pl-5 sm:pl-7">
            {/* Pulsing indicator dot */}
            <div className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.8)] border-4 border-slate-950" />

            <div className="glass-panel p-4 sm:p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md transition-all hover:border-slate-600">
              <div className="flex flex-wrap justify-between items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-cyan-400 font-mono">
                  {new Date(entry.date).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
                <span className="badge badge-interview text-[11px]">{entry.appearance_type}</span>
              </div>

              <h4 className="text-base font-semibold text-slate-100">{entry.title}</h4>
              <p className="text-xs text-slate-400 mt-1">
                Publisher: <span className="text-slate-300 font-medium">{entry.publisher || 'External Media'}</span>
              </p>

              {entry.summary && (
                <p className="text-sm text-slate-300 mt-2.5 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800">
                  {entry.summary}
                </p>
              )}

              {entry.primary_source_url && (
                <a
                  href={entry.primary_source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium mt-3 transition-colors"
                >
                  <span>Inspect Original Source</span>
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
