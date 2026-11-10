import React from 'react';
import { Quote } from 'lucide-react';

export default function EvidenceQuotes({ statements }) {
  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
      <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
        <Quote size={16} className="text-amber-600" />
        <span>Key Quotes & Statements</span>
      </h4>
      <div className="flex flex-col gap-3">
        {statements && statements.length > 0 ? (
          statements.slice(0, 4).map((stmt, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-lg bg-slate-50 border-l-4 border-amber-500 border-r border-t border-b border-slate-200"
            >
              <p className="text-sm italic text-slate-800 leading-relaxed">
                "{stmt.statement}"
              </p>
              <p className="text-xs text-slate-500 mt-1.5 font-medium">
                Source: <span className="text-slate-700">{stmt.source_title || 'Media Appearance'}</span>
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
