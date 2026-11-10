import React, { useState } from 'react';
import {
  Sparkles,
  RotateCw,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  Briefcase,
  Heart,
  BookOpen,
  Building2,
  Calendar,
  TrendingUp,
  Target,
  ExternalLink,
  Clock,
  AlertTriangle
} from 'lucide-react';
import DownloadMenu from './DownloadMenu';
import { downloadPersonReport } from '../../utils/exportReport';

const SECTION_CONFIG = [
  {
    key: 'professional_insights',
    title: '1. Professional Insights',
    subtitle: 'Current role, career background, experience & leadership credentials',
    icon: Briefcase,
    accentClass: 'text-blue-600 bg-blue-50 border-blue-200',
  },
  {
    key: 'interest_insights',
    title: '2. Interest Insights',
    subtitle: 'Frequently discussed topics, technology interests & recurring themes',
    icon: Heart,
    accentClass: 'text-pink-600 bg-pink-50 border-pink-200',
  },
  {
    key: 'knowledge_and_expertise',
    title: '3. Knowledge and Expertise',
    subtitle: 'Demonstrated subject-matter depth, technical & industry expertise',
    icon: BookOpen,
    accentClass: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  },
  {
    key: 'company_insights',
    title: '4. Company Insights',
    subtitle: 'Organization activities, products/services, business model & initiatives',
    icon: Building2,
    accentClass: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  },
  {
    key: 'recent_activities',
    title: '5. Recent Activities',
    subtitle: 'Notable posts, interviews, podcasts & company announcements',
    icon: Calendar,
    accentClass: 'text-cyan-700 bg-cyan-50 border-cyan-200',
  },
  {
    key: 'business_insights',
    title: '6. Business Insights',
    subtitle: 'Publicly discussed challenges, priorities, opportunities & investigation leads',
    icon: TrendingUp,
    accentClass: 'text-amber-700 bg-amber-50 border-amber-200',
  },
  {
    key: 'key_takeaways',
    title: '7. Key Takeaways',
    subtitle: 'Key observations, potential project/tech ideas & actionable conclusions',
    icon: Target,
    accentClass: 'text-violet-700 bg-violet-50 border-violet-200',
  },
];

function ConfidencePill({ level }) {
  const styles =
    level === 'HIGH'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : level === 'LOW'
      ? 'bg-slate-100 text-slate-600 border-slate-300'
      : 'bg-blue-50 text-blue-700 border-blue-200';
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${styles}`}>
      {level} Confidence
    </span>
  );
}

function ClaimTypePill({ claimType }) {
  if (claimType === 'AI_HYPOTHESIS') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
        <Lightbulb size={11} />
        <span>AI Hypothesis</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
      <CheckCircle2 size={11} />
      <span>Verified Fact</span>
    </span>
  );
}

export default function AIInsightsPanel({
  person = null,
  personName,
  appearances = [],
  sources = [],
  insightsHistory,
  onGenerateInsights,
}) {
  const [focusNotes, setFocusNotes] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState(null);

  const historyList = Array.isArray(insightsHistory?.history) ? insightsHistory.history : [];
  const activeReport =
    historyList.find((r) => r.id === selectedReportId) ||
    insightsHistory?.latest_report ||
    historyList[0] ||
    null;

  async function handleGenerate(e) {
    if (e) e.preventDefault();
    if (!onGenerateInsights || generating) return;
    setGenerating(true);
    setError(null);
    try {
      const created = await onGenerateInsights(focusNotes.trim() || null);
      if (created?.id) {
        setSelectedReportId(created.id);
      }
    } catch (err) {
      setError(err.message || 'Failed to generate AI insights.');
    } finally {
      setGenerating(false);
    }
  }

  const reportPayload = activeReport?.report || null;
  const coverage = reportPayload?.data_coverage || {};

  return (
    <div className="flex flex-col gap-5">
      {/* Control Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Sparkles size={20} className="text-blue-600" />
              <span>AI Insights Generator</span>
            </h3>
            <p className="text-sm text-slate-600 mt-1">
              Synthesizes stored LinkedIn data, web articles, transcripts, and interviews for{' '}
              <span className="font-semibold text-slate-900">{personName}</span> with zero extra credit cost.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            {historyList.length > 0 && (
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-slate-500" />
                <select
                  value={activeReport?.id || ''}
                  onChange={(e) => setSelectedReportId(e.target.value)}
                  className="input-field text-xs py-2 px-3 w-auto min-w-[200px] bg-white"
                  aria-label="Select insights report version"
                >
                  {historyList.map((rep, idx) => (
                    <option key={rep.id} value={rep.id}>
                      {idx === 0 ? 'Latest • ' : `v${historyList.length - idx} • `}
                      {new Date(rep.generated_at).toLocaleString()} ({rep.model_name})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={generating}
              className="btn btn-primary text-xs sm:text-sm px-4 py-2.5"
            >
              {generating ? (
                <>
                  <RotateCw size={15} className="animate-spin" />
                  <span>Generating Insights...</span>
                </>
              ) : (
                <>
                  <Sparkles size={15} />
                  <span>{activeReport ? 'Regenerate Insights' : 'Generate Insights'}</span>
                </>
              )}
            </button>

            <DownloadMenu
              personName={personName}
              disabled={!activeReport || generating}
              buttonLabel="Download"
              buttonClassName="btn btn-secondary text-xs sm:text-sm px-3.5 py-2.5"
              onDownloadPerson={(format) =>
                downloadPersonReport({
                  format,
                  person: person || { name: personName },
                  appearances,
                  sources,
                  insightsReport: activeReport,
                })
              }
            />
          </div>
        </div>

        {/* Optional Simple Focus Field */}
        <form onSubmit={handleGenerate} className="mt-4 pt-4 border-t border-slate-100 flex flex-col sm:flex-row gap-2.5">
          <input
            type="text"
            value={focusNotes}
            onChange={(e) => setFocusNotes(e.target.value)}
            placeholder="Optional question or focus area (e.g., fintech partnerships, technology adoption, sales priorities)..."
            className="input-field text-xs sm:text-sm py-2 flex-1"
            disabled={generating}
          />
        </form>

        {/* Loading & Error Feedback */}
        {generating && (
          <div className="mt-4 p-3.5 rounded-xl border border-blue-200 bg-blue-50 flex items-center gap-2.5 text-sm text-blue-800">
            <RotateCw size={16} className="animate-spin shrink-0" />
            <span>Analyzing collected records and building structured insights with citations...</span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3.5 rounded-xl border border-rose-200 bg-rose-50 flex items-center gap-2.5 text-sm text-rose-700">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Empty State */}
      {!reportPayload ? (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center shadow-sm">
          <Sparkles size={32} className="mx-auto mb-3 text-blue-500 opacity-75" />
          <h4 className="text-base font-bold text-slate-900">No AI Insights Generated Yet</h4>
          <p className="text-sm text-slate-600 mt-1.5 max-w-md mx-auto">
            Click <strong>Generate Insights</strong> above to synthesize all stored LinkedIn records, posts, transcripts, and articles into 7 clear briefing sections.
          </p>
        </div>
      ) : (
        <>
          {/* Executive Summary & Metadata Bar */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                Executive Overview
              </h4>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                <span className="px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-medium">
                  Model: {activeReport.model_name}
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-medium">
                  Prompt: {activeReport.prompt_version}
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-medium">
                  Time: {activeReport.generation_time_seconds}s
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                  {activeReport.source_count} Sources Analyzed
                </span>
              </div>
            </div>

            <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
              {reportPayload.executive_overview}
            </p>

            {/* Data Coverage Pills */}
            <div className="flex flex-wrap gap-2 mt-3.5 text-xs text-slate-600">
              <span className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                LinkedIn Enriched: <strong>{coverage.linkedin_profile_enriched ? 'Yes' : 'No'}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                LinkedIn Posts: <strong>{coverage.linkedin_posts || 0}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                YouTube & Podcasts: <strong>{coverage.youtube_and_podcasts || 0}</strong>
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200">
                News & Web Articles: <strong>{coverage.articles_and_news || 0}</strong>
              </span>
            </div>
          </div>

          {/* Seven Required Insight Sections */}
          <div className="grid grid-cols-1 gap-5">
            {SECTION_CONFIG.map((cfg) => {
              const Icon = cfg.icon;
              const sec = reportPayload[cfg.key] || {
                insufficient_evidence: true,
                insufficient_evidence_note: 'No data available.',
                items: [],
              };

              return (
                <section
                  key={cfg.key}
                  className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-4 border-b border-slate-100">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-xl border shrink-0 ${cfg.accentClass}`}>
                        <Icon size={18} />
                      </div>
                      <div>
                        <h4 className="text-base font-bold text-slate-900">{cfg.title}</h4>
                        <p className="text-xs text-slate-500 mt-0.5">{cfg.subtitle}</p>
                      </div>
                    </div>

                    {sec.insufficient_evidence && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 self-start sm:self-center">
                        <AlertTriangle size={12} />
                        <span>Insufficient Evidence</span>
                      </span>
                    )}
                  </div>

                  {sec.summary && (
                    <p className="text-sm text-slate-700 mb-4 leading-relaxed">
                      {sec.summary}
                    </p>
                  )}

                  {sec.insufficient_evidence && sec.insufficient_evidence_note && (
                    <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 text-xs sm:text-sm text-amber-800 mb-3 flex items-start gap-2">
                      <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                      <span>{sec.insufficient_evidence_note}</span>
                    </div>
                  )}

                  {sec.items && sec.items.length > 0 && (
                    <div className="space-y-3">
                      {sec.items.map((item, idx) => (
                        <div
                          key={`${item.title}-${idx}`}
                          className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 hover:border-slate-300 transition-colors"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                            <div className="flex flex-wrap items-center gap-2">
                              <h5 className="text-sm font-bold text-slate-900">{item.title}</h5>
                              {item.sub_category && (
                                <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-white text-slate-600 border border-slate-200">
                                  {item.sub_category}
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap items-center gap-1.5">
                              <ClaimTypePill claimType={item.claim_type} />
                              <ConfidencePill level={item.confidence} />
                            </div>
                          </div>

                          <p className="text-sm text-slate-700 leading-relaxed">{item.detail}</p>

                          {item.supporting_sources && item.supporting_sources.length > 0 && (
                            <div className="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-slate-200/70">
                              <span className="text-[11px] font-semibold text-slate-500">Sources:</span>
                              {item.supporting_sources.map((src, sIdx) => (
                                <span key={sIdx} className="inline-flex items-center gap-1 text-xs">
                                  {src.url ? (
                                    <a
                                      href={src.url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-blue-600 hover:text-blue-800 hover:border-blue-300 transition-colors"
                                    >
                                      <span className="max-w-[200px] truncate">{src.title || src.source_type || 'Source'}</span>
                                      {src.published_at && (
                                        <span className="text-slate-400">({src.published_at})</span>
                                      )}
                                      <ExternalLink size={10} />
                                    </a>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600">
                                      {src.title || src.source_type || 'Profile Record'}
                                      {src.published_at ? ` (${src.published_at})` : ''}
                                    </span>
                                  )}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

