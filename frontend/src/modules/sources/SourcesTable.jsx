import React from 'react';
import { ExternalLink } from 'lucide-react';

export default function SourcesTable({ sources }) {
  return (
    <div className="bg-white rounded-xl overflow-hidden border border-slate-200 shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[500px]">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-600">
              <th className="py-3 px-4 sm:px-5">Source Type</th>
              <th className="py-3 px-4 sm:px-5">URL Reference</th>
              <th className="py-3 px-4 sm:px-5">Extraction Status</th>
              <th className="py-3 px-4 sm:px-5">Collected At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sources.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-slate-500">
                  No source provenance entries found.
                </td>
              </tr>
            ) : (
              sources.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 transition-colors">
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
                  <td className="py-3 px-4 sm:px-5 text-xs text-slate-500 font-mono">
                    {new Date(s.collected_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
