import React, { useState } from 'react';
import { Link2, Sparkles, AlertCircle, CheckCircle2, RotateCw, X } from 'lucide-react';
import { api } from '../../api';

export default function UrlUploadModal({ isOpen, onClose, personId, personName, onAppearanceCreated }) {
  const [url, setUrl] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.analyzeUrl(personId, {
        url: url.trim(),
        source_type: sourceType || null,
        title: customTitle.trim() || null,
      });

      setResult(res);
      if (onAppearanceCreated) {
        onAppearanceCreated(res);
      }
    } catch (err) {
      setError(err.message || 'Failed to extract and analyze URL');
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setUrl('');
    setSourceType('');
    setCustomTitle('');
    setError(null);
    setResult(null);
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="glass-panel w-full max-w-lg rounded-2xl p-6 bg-slate-900 border border-slate-700/80 shadow-2xl">
        <div className="flex justify-between items-center mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Link2 size={20} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100">Upload & Analyze Public URL</h3>
              <p className="text-xs text-slate-400">
                Target: <span className="text-cyan-400 font-semibold">{personName}</span>
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              handleReset();
              onClose();
            }}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2 mb-4">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result ? (
          <div className="flex flex-col gap-4">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm mb-1.5">
                <CheckCircle2 size={18} />
                <span>URL Extracted & Analyzed!</span>
              </div>
              <p className="text-sm font-semibold text-slate-200">{result.title}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="badge badge-interview">{result.appearance_type}</span>
                <span className="badge badge-verified">
                  {result.identity_status} ({Math.round(result.confidence_score * 100)}%)
                </span>
                {result.analysis?.person_role && (
                  <span className="text-xs text-cyan-400 font-medium">Role: {result.analysis.person_role}</span>
                )}
              </div>
              {result.analysis?.summary && (
                <p className="text-xs text-slate-300 mt-2.5 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800">
                  {result.analysis.summary}
                </p>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button onClick={handleReset} className="btn btn-secondary">
                Upload Another URL
              </button>
              <button
                onClick={() => {
                  handleReset();
                  onClose();
                }}
                className="btn btn-primary"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Public URL to Analyze *
              </label>
              <input
                type="url"
                required
                placeholder="https://www.youtube.com/watch?v=... or https://news.com/article/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="input-field"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Supports YouTube videos, podcasts, news articles, interviews, and conference pages.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Media Format (Optional)
                </label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="input-field"
                >
                  <option value="">Auto-Detect Format</option>
                  <option value="YOUTUBE">YouTube Video</option>
                  <option value="PODCAST">Podcast Episode</option>
                  <option value="NEWS">News Article</option>
                  <option value="EVENT">Conference / Webinar</option>
                  <option value="WEBPAGE">Webpage / Blog</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Title Override (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Keynote at TechSummit 2026"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="input-field"
                />
              </div>
            </div>

            <div className="border-t border-slate-800 pt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  handleReset();
                  onClose();
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" disabled={loading} className="btn btn-primary">
                {loading ? (
                  <>
                    <RotateCw size={15} className="animate-spin" />
                    <span>Extracting & Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={15} />
                    <span>Ingest & Analyze</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
