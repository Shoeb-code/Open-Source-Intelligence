import React from 'react';
import { ExternalLink, Trash2 } from 'lucide-react';

export default function AppearanceCard({ item, onDelete }) {
  const badgeTypeClass =
    item.appearance_type === 'PODCAST'
      ? 'badge-podcast'
      : item.appearance_type === 'INTERVIEW'
      ? 'badge-interview'
      : item.appearance_type === 'CONFERENCE'
      ? 'badge-conference'
      : 'badge-news';

  const badgeStatusClass =
    item.identity_status === 'VERIFIED'
      ? 'badge-verified'
      : item.identity_status === 'LIKELY_MATCH'
      ? 'badge-likely'
      : 'badge-review';

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md flex flex-col gap-3 transition-all hover:border-slate-600">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className={`badge ${badgeTypeClass}`}>{item.appearance_type}</span>
            <span className={`badge ${badgeStatusClass}`}>{item.identity_status}</span>
            <span className="text-xs text-slate-400 font-mono">
              Score: {Math.round(item.confidence_score * 100)}%
            </span>
          </div>

          <h4 className="text-base font-semibold text-slate-100 hover:text-cyan-400 transition-colors">
            {item.title}
          </h4>

          <p className="text-xs text-slate-400 mt-1">
            Publisher: <span className="text-slate-300 font-medium">{item.publisher || 'Web / Media'}</span> •{' '}
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
              className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg border border-transparent hover:border-rose-500/30 transition-all"
              title="Delete appearance"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {item.analysis?.summary && (
        <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800">
          {item.analysis.summary}
        </p>
      )}

      <div className="flex flex-wrap gap-2 items-center pt-1 border-t border-slate-800/80">
        {item.analysis?.person_role && (
          <span className="inline-flex items-center text-xs px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-cyan-400 font-semibold tracking-wide">
            Role: {item.analysis.person_role}
          </span>
        )}
        {item.analysis?.topics?.map((topic, i) => (
          <span
            key={i}
            className="text-xs px-2.5 py-0.5 rounded bg-slate-800/60 text-slate-400 border border-slate-700/50"
          >
            #{topic}
          </span>
        ))}
        {item.analysis?.model_name && (
          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800/40 text-slate-400 border border-slate-800 font-mono ml-auto">
            {item.analysis.model_name}
          </span>
        )}
      </div>
    </div>
  );
}
