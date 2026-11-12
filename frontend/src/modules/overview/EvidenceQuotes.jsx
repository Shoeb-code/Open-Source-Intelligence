import React from 'react';
import { Quote } from 'lucide-react';

export default function EvidenceQuotes({ statements }) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
      <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
        <span className="p-1.5 rounded-lg bg-amber-50 text-amber-600 border border-amber-100">
          <Quote size={15} />
        </span>
        <span>Key Quotes &amp; Statements</span>
      </h4>
      <div className="flex flex-col gap-3">
        {statements && statements.length > 0 ? (
          statements.slice(0, 4).map((stmt, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-50/80 border-l-4 border-l-amber-500 border border-slate-200"
            >
              <p className="text-sm italic text-slate-800 leading-relaxed">
                &ldquo;{stmt.statement}&rdquo;
              </p>
              <p className="text-xs text-slate-500 mt-2 font-medium">
                Source: <span className="text-slate-700 font-semibold">{stmt.source_title || 'Media Appearance'}</span>
              </p>
            </div>
          ))
        ) : (
          <p className="text-xs text-slate-500">
            Direct evidence quotes will appear here after analysis.
          </p>
        )}
      </div>
    </div>
  );
}
