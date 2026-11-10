import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, FileText } from 'lucide-react';

export default function SourcesTable({ sources }) {
  const [expandedId, setExpandedId] = useState(null);

  return (
    <div className="bg-white rounded-xl overflow-hidden border border-slate-200 shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[640px]">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-600">
              <th className="py-3 px-4 sm:px-5">Source Type</th>
              <th className="py-3 px-4 sm:px-5">URL Reference</th>
              <th className="py-3 px-4 sm:px-5">Extraction Status</th>
              <th className="py-3 px-4 sm:px-5">Extracted Post / Transcript</th>
              <th className="py-3 px-4 sm:px-5">Collected At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sources.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No source provenance entries found.
                </td>
              </tr>
            ) : (
              sources.map((s) => {
                const text = s.extracted_content?.trim() || '';
                const isOpen = expandedId === s.id;
                return (
                  <React.Fragment key={s.id}>
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 sm:px-5 font-semibold text-slate-800">
                        <span className="font-mono text-xs">{s.source_type}</span>
                      </td>
                      <td className="py-3 px-4 sm:px-5 max-w-xs truncate">
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:text-blue-800 font-mono text-xs inline-flex items-center gap-1.5 transition-colors"
                        >
                          <span className="truncate">{s.source_url}</span>
                          <ExternalLink size={12} className="shrink-0" />
                        </a>
                      </td>
                      <td className="py-3 px-4 sm:px-5">
                        <span
                          className={`badge ${
                            s.extraction_status === 'SUCCESS' || s.extraction_status === 'AI_TRANSCRIBED'
                              ? 'badge-verified'
                              : s.extraction_status === 'METADATA_FALLBACK'
                              ? 'badge-likely'
                              : 'badge-review'
                          }`}
                        >
                          {s.extraction_status}
                        </span>
                      </td>
                      <td className="py-3 px-4 sm:px-5">
                        {text ? (
                          <button
                            type="button"
                            onClick={() => setExpandedId(isOpen ? null : s.id)}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-900 px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-200 transition-colors"
                          >
                            <FileText size={12} />
                            <span>{isOpen ? 'Hide' : `View (${text.length.toLocaleString()} chars)`}</span>
                            {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </button>
                        ) : (
                          <span className="text-xs text-slate-400 italic">No content captured</span>
                        )}
                      </td>
                      <td className="py-3 px-4 sm:px-5 text-xs text-slate-500 font-mono">
                        {new Date(s.collected_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {isOpen && text && (
                      <tr className="bg-slate-50/70">
                        <td colSpan={5} className="p-4 border-t border-slate-100">
                          <div className="bg-white rounded-lg border border-slate-200 p-3.5 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto">
                            {text}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
