import React from 'react';
import { Quote } from 'lucide-react';

export default function EvidenceQuotes({ statements }) {
  return (
    <div className="glass-panel p-6 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
      <h4 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Quote size={16} className="text-amber-400" />
        <span>Extracted Statements & Evidence</span>
      </h4>
      <div className="flex flex-col gap-3">
        {statements && statements.length > 0 ? (
          statements.slice(0, 4).map((stmt, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-lg bg-slate-800/60 border-l-4 border-amber-400 border-r border-t border-b border-slate-700/50"
            >
              <p className="text-sm italic text-slate-200 leading-relaxed">
                "{stmt.statement}"
              </p>
              <p className="text-xs text-slate-400 mt-1.5 font-medium">
                Source: <span className="text-slate-300">{stmt.source_title || 'Media Appearance'}</span>
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
