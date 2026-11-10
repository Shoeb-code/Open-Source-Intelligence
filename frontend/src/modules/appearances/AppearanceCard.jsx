import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, CheckCircle2, Trash2 } from 'lucide-react';

export default function AppearanceCard({ item, onDelete }) {
  const [expanded, setExpanded] = useState(false);

  const badgeTypeClass =
    item.appearance_type === 'PODCAST'
      ? 'badge-podcast'
      : item.appearance_type === 'INTERVIEW'
      ? 'badge-interview'
      : item.appearance_type === 'CONFERENCE'
      ? 'badge-conference'
      : item.appearance_type === 'INSTAGRAM_POST'
      ? 'badge-instagram'
      : item.appearance_type === 'INSTAGRAM_REEL'
      ? 'badge-reel'
      : item.appearance_type === 'LINKEDIN_POST'
      ? 'badge-linkedin'
      : 'badge-news';

  const badgeStatusClass =
    item.identity_status === 'VERIFIED'
      ? 'badge-verified'
      : item.identity_status === 'LIKELY_MATCH'
      ? 'badge-likely'
      : 'badge-review';

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 flex flex-col gap-3 transition-all hover:border-slate-300 shadow-xs">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className={`badge ${badgeTypeClass}`}>{item.appearance_type}</span>
            <span className={`badge ${badgeStatusClass}`}>{item.identity_status}</span>
            <span className="text-xs text-slate-500 font-mono">
              Score: {Math.round(item.confidence_score * 100)}%
            </span>
          </div>

          <h4 className="text-base font-semibold text-slate-900">
            {item.title}
          </h4>

          <p className="text-xs text-slate-500 mt-1">
            Publisher: <span className="text-slate-700 font-medium">{item.publisher || 'Web / Media'}</span> •{' '}
            {item.published_at ? new Date(item.published_at).toLocaleDateString() : 'Recent'}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {item.sources?.[0] && (
            <a
              href={item.sources[0].source_url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary text-xs px-3.5 py-1.5 whitespace-nowrap"
            >
              <span>View Source</span>
              <ExternalLink size={13} />
            </a>
          )}
          {onDelete && (
            <button
              onClick={() => {
                if (window.confirm(`Delete "${item.title}"?`)) {
                  onDelete(item.id);
                }
              }}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-transparent hover:border-rose-200 transition-all"
              title="Delete appearance"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {item.analysis?.summary && (
        <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
          {item.analysis.summary}
        </p>
      )}

      {item.analysis?.key_points && item.analysis.key_points.length > 0 && (
        <div className="bg-slate-50 rounded-lg border border-slate-200 overflow-hidden">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between p-2.5 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-blue-700">
              <CheckCircle2 size={13} />
              <span>Key Points ({item.analysis.key_points.length})</span>
            </span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {expanded && (
            <ul className="px-3.5 pb-3 pt-1 space-y-1.5 border-t border-slate-200 text-xs text-slate-700 list-disc list-inside bg-white">
              {item.analysis.key_points.map((kp, idx) => (
                <li key={idx} className="leading-relaxed">
                  {kp}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2 items-center pt-2 border-t border-slate-100">
        {item.analysis?.person_role && (
          <span className="inline-flex items-center text-xs px-2.5 py-0.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700 font-semibold">
            Role: {item.analysis.person_role}
          </span>
        )}
        {item.analysis?.topics?.map((topic, i) => (
          <span
            key={i}
            className="text-xs px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200"
          >
            #{topic}
          </span>
        ))}
        {item.analysis?.model_name && (
          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-50 text-slate-500 border border-slate-200 font-mono ml-auto">
            {item.analysis.model_name}
          </span>
        )}
      </div>
    </div>
  );
}
