import React, { useMemo, useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, FileText, Search, X, Copy, Check } from 'lucide-react';

export default function SourcesTable({ sources }) {
  const [expandedId, setExpandedId] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [query, setQuery] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const summary = useMemo(() => {
    const total = sources.length;
    const success = sources.filter(
      (s) => s.extraction_status === 'SUCCESS' || s.extraction_status === 'AI_TRANSCRIBED'
    ).length;
    const fallback = sources.filter((s) => s.extraction_status === 'METADATA_FALLBACK').length;
    const failed = sources.filter(
      (s) =>
        s.extraction_status === 'FAILED' ||
        s.extraction_status === 'RESTRICTED' ||
        s.extraction_status === 'TRANSCRIPT_UNAVAILABLE'
    ).length;
    return { total, success, fallback, failed };
  }, [sources]);

  const filteredSources = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sources.filter((s) => {
      if (statusFilter === 'SUCCESS') {
        if (s.extraction_status !== 'SUCCESS' && s.extraction_status !== 'AI_TRANSCRIBED') return false;
      } else if (statusFilter === 'ISSUES') {
        if (
          s.extraction_status !== 'FAILED' &&
          s.extraction_status !== 'RESTRICTED' &&
          s.extraction_status !== 'TRANSCRIPT_UNAVAILABLE'
        ) {
          return false;
        }
      } else if (statusFilter !== 'ALL' && s.extraction_status !== statusFilter) {
        return false;
      }

      if (q) {
        const hay = `${s.source_type || ''} ${s.source_url || ''} ${s.extracted_content || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [sources, statusFilter, query]);

  async function handleCopy(id, text) {
    if (!text || typeof navigator === 'undefined' || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId((prev) => (prev === id ? null : prev)), 1800);
    } catch {
      setCopiedId(null);
    }
  }

  return (
    <div className="space-y-4">
      {/* Compact Source Provenance KPI & Filter Bar */}
      <div className="bg-slate-50/90 p-3.5 rounded-2xl border border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'ALL', label: 'All Sources', count: summary.total },
            { id: 'SUCCESS', label: 'Extracted', count: summary.success },
            { id: 'METADATA_FALLBACK', label: 'Fallback Snippet', count: summary.fallback },
            { id: 'ISSUES', label: 'Restricted / Failed', count: summary.failed },
          ].map((pill) => (
            <button
              key={pill.id}
              type="button"
              onClick={() => setStatusFilter(pill.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border inline-flex items-center gap-1.5 transition-all ${
                statusFilter === pill.id
                  ? 'bg-blue-600 border-blue-600 text-white shadow-xs'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span>{pill.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  statusFilter === pill.id ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {pill.count}
              </span>
            </button>
          ))}
        </div>

        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter URLs or extracted text..."
            className="pl-8 pr-7 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 w-full lg:w-64"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
              aria-label="Clear source filter"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl overflow-hidden border border-slate-200 shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[640px]">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-600">
                <th className="py-3.5 px-4 sm:px-5">Source Type</th>
                <th className="py-3.5 px-4 sm:px-5">URL Reference</th>
                <th className="py-3.5 px-4 sm:px-5">Extraction Status</th>
                <th className="py-3.5 px-4 sm:px-5">Extracted Post / Transcript</th>
                <th className="py-3.5 px-4 sm:px-5">Collected At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredSources.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-500 text-xs">
                    {sources.length === 0
                      ? 'No source provenance entries found yet.'
                      : 'No sources match the active filter.'}
                  </td>
                </tr>
              ) : (
                filteredSources.map((s) => {
                  const text = s.extracted_content?.trim() || '';
                  const isOpen = expandedId === s.id;
                  const statusBadge =
                    s.extraction_status === 'SUCCESS' || s.extraction_status === 'AI_TRANSCRIBED'
                      ? 'badge-verified'
                      : s.extraction_status === 'METADATA_FALLBACK'
                      ? 'badge-likely'
                      : s.extraction_status === 'FAILED'
                      ? 'badge-rejected'
                      : 'badge-review';

                  return (
                    <React.Fragment key={s.id}>
                      <tr className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 sm:px-5 font-semibold text-slate-800">
                          <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            {s.source_type}
                          </span>
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
                          <span className={`badge ${statusBadge}`}>{s.extraction_status}</span>
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
                        <tr className="bg-slate-50/80">
                          <td colSpan={5} className="p-4 border-t border-slate-100">
                            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                              <div className="flex items-center justify-between px-3.5 py-2 bg-slate-50/80 border-b border-slate-100 text-[11px] text-slate-500">
                                <span className="font-mono">{text.length.toLocaleString()} characters captured</span>
                                <button
                                  type="button"
                                  onClick={() => handleCopy(s.id, text)}
                                  className="inline-flex items-center gap-1 font-semibold text-slate-600 hover:text-blue-700 px-2 py-0.5 rounded bg-white border border-slate-200"
                                >
                                  {copiedId === s.id ? (
                                    <Check size={12} className="text-emerald-600" />
                                  ) : (
                                    <Copy size={12} />
                                  )}
                                  <span>{copiedId === s.id ? 'Copied' : 'Copy'}</span>
                                </button>
                              </div>
                              <div className="p-3.5 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto">
                                {text}
                              </div>
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
    </div>
  );
}
