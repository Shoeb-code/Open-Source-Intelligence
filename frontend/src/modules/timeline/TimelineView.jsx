import React from 'react';
import { Calendar, ExternalLink } from 'lucide-react';

export default function TimelineView({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 max-w-2xl mx-auto shadow-xs">
        <Calendar size={36} className="mx-auto mb-3 text-slate-400 opacity-50" />
        <h4 className="text-sm font-semibold text-slate-800">No timeline entries yet</h4>
        <p className="text-xs text-slate-500 mt-1">
          Appearances with publication dates will be plotted chronologically here.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-2 sm:py-4">
      <div className="relative border-l-2 border-blue-200 ml-2.5 sm:ml-4 space-y-5 sm:space-y-6">
        {timeline.map((entry, idx) => (
          <div key={idx} className="relative pl-5 sm:pl-7">
            <div className="absolute -left-[9px] top-2 w-4 h-4 rounded-full bg-blue-600 border-4 border-white shadow-sm ring-1 ring-blue-200" />

            <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs transition-all hover:border-blue-300 hover:shadow-sm">
              <div className="flex flex-wrap justify-between items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-blue-700 font-mono bg-blue-50 px-2.5 py-0.5 rounded-md border border-blue-100">
                  {new Date(entry.date).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
                <span className="badge badge-interview text-[11px]">{entry.appearance_type}</span>
              </div>

              <h4 className="text-base font-bold text-slate-900">{entry.title}</h4>
              <p className="text-xs text-slate-500 mt-1">
                Publisher: <span className="text-slate-700 font-medium">{entry.publisher || 'External Media'}</span>
              </p>

              {entry.summary && (
                <p className="text-sm text-slate-700 mt-3 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200/80">
                  {entry.summary}
                </p>
              )}

              {entry.primary_source_url && (
                <a
                  href={entry.primary_source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-semibold mt-3 transition-colors"
                >
                  <span>View Original Source</span>
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
