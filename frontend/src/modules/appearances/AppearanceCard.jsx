import React, { useState } from 'react';
import {
  ExternalLink,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Trash2,
  FileText,
  Copy,
  Check,
} from 'lucide-react';

export default function AppearanceCard({ item, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const primarySource =
    item.sources?.find((s) => s.extracted_content && s.extracted_content.trim()) ||
    item.sources?.[0] ||
    null;
  const extractedContent = primarySource?.extracted_content?.trim() || '';
  const sourceTypeUpper = (primarySource?.source_type || '').toUpperCase();
  const contentLabel =
    sourceTypeUpper === 'YOUTUBE'
      ? 'YouTube Transcript / Video Details'
      : sourceTypeUpper === 'LINKEDIN' || item.appearance_type === 'LINKEDIN_POST'
      ? 'Extracted LinkedIn Post / Article'
      : 'Extracted Content';

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

  async function handleCopy() {
    if (!extractedContent || typeof navigator === 'undefined' || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(extractedContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 flex flex-col gap-3 transition-all hover:border-slate-300 hover:shadow-sm shadow-xs">
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span className={`badge ${badgeTypeClass}`}>{item.appearance_type}</span>
            <span className={`badge ${badgeStatusClass}`}>{item.identity_status}</span>
            <span className="text-xs text-slate-500 font-mono bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200/80">
              {Math.round(item.confidence_score * 100)}% match
            </span>
          </div>

          <h4 className="text-base font-bold text-slate-900 leading-snug">{item.title}</h4>

          <p className="text-xs text-slate-500 mt-1">
            Publisher:{' '}
            <span className="text-slate-700 font-semibold">{item.publisher || 'Web / Media'}</span>{' '}
            &bull; {item.published_at ? new Date(item.published_at).toLocaleDateString() : 'Recent'}
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
          {onDelete && !confirmDelete && (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-transparent hover:border-rose-200 transition-all"
              title="Delete appearance"
              aria-label={`Delete ${item.title}`}
            >
              <Trash2 size={14} />
            </button>
          )}
          {onDelete && confirmDelete && (
            <div className="flex items-center gap-1 text-xs">
              <button
                type="button"
                onClick={() => {
                  setConfirmDelete(false);
                  onDelete(item.id);
                }}
                className="px-2.5 py-1 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700"
              >
                Delete
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-2 py-1 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {item.analysis?.summary && (
        <p className="text-sm text-slate-700 leading-relaxed bg-slate-50/90 p-3.5 rounded-xl border border-slate-200/80">
          {item.analysis.summary}
        </p>
      )}

      {item.analysis?.key_points && item.analysis.key_points.length > 0 && (
        <div className="bg-slate-50 rounded-xl border border-slate-200 overflow-hidden">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between p-2.5 px-3 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-blue-700">
              <CheckCircle2 size={13} />
              <span>Key Points ({item.analysis.key_points.length})</span>
            </span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {expanded && (
            <ul className="px-4 pb-3.5 pt-2 space-y-1.5 border-t border-slate-200 text-xs text-slate-700 list-disc list-inside bg-white">
              {item.analysis.key_points.map((kp, idx) => (
                <li key={idx} className="leading-relaxed">
                  {kp}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {extractedContent && (
        <div className="bg-slate-50 rounded-xl border border-slate-200 overflow-hidden">
          <button
            type="button"
            onClick={() => setShowContent(!showContent)}
            className="w-full flex items-center justify-between p-2.5 px-3 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <span className="flex items-center gap-1.5 uppercase tracking-wider text-[11px] text-emerald-700">
              <FileText size={13} />
              <span>
                {contentLabel} ({extractedContent.length.toLocaleString()} chars)
              </span>
            </span>
            <span className="flex items-center gap-2">
              {primarySource?.extraction_status && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                  {primarySource.extraction_status}
                </span>
              )}
              {showContent ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </span>
          </button>
          {showContent && (
            <div className="border-t border-slate-200 bg-white">
              <div className="flex justify-end px-3 pt-2">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 hover:text-blue-700 px-2 py-1 rounded-md bg-slate-50 border border-slate-200 transition-colors"
                >
                  {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied' : 'Copy Text'}</span>
                </button>
              </div>
              <div className="p-3.5 pt-2 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto font-sans">
                {extractedContent}
              </div>
            </div>
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
      </div>
    </div>
  );
}
