import React, { useState, useMemo } from 'react';
import {
  User,
  ShieldCheck,
  ExternalLink,
  Play,
  RotateCw,
  Search,
  CheckCircle2,
  Layers,
  Sparkles,
  Link2,
  Globe
} from 'lucide-react';
import AppearanceCard from '../appearances/AppearanceCard';

export default function TargetAccountPage({
  person,
  appearances = [],
  sources = [],
  reportData,
  onStartResearch,
  isResearching = false,
  onOpenUrlModal,
  onDeleteAppearance
}) {
  const [activeMediaFilter, setActiveMediaFilter] = useState('ALL'); // ALL, LINKEDIN, INSTAGRAM, YOUTUBE, NEWS
  const [searchQuery, setSearchQuery] = useState('');

  // Extract Social Profiles
  const linkedinProfile = person?.social_profiles?.find((p) => p.platform === 'linkedin');
  const instagramProfile = person?.social_profiles?.find((p) => p.platform === 'instagram');
  const youtubeProfile = person?.social_profiles?.find((p) => p.platform === 'youtube');
  const otherProfiles = person?.social_profiles?.filter(
    (p) => !['linkedin', 'instagram', 'youtube'].includes(p.platform)
  ) || [];

  // Only count verified or non-rejected appearances
  const validAppearances = useMemo(() => {
    return appearances.filter((a) => a.identity_status !== 'REJECTED');
  }, [appearances]);

  // Grouped Appearance Counts
  const linkedinCount = validAppearances.filter(
    (a) =>
      a.appearance_type === 'LINKEDIN_POST' ||
      a.appearance_type === 'ARTICLE' ||
      (a.sources?.[0]?.source_url || '').includes('linkedin.com')
  ).length;

  const instagramCount = validAppearances.filter(
    (a) =>
      a.appearance_type === 'INSTAGRAM_POST' ||
      a.appearance_type === 'INSTAGRAM_REEL' ||
      (a.sources?.[0]?.source_url || '').includes('instagram.com')
  ).length;

  const youtubeCount = validAppearances.filter(
    (a) =>
      a.appearance_type === 'PODCAST' ||
      a.appearance_type === 'INTERVIEW' ||
      (a.sources?.[0]?.source_url || '').includes('youtube.com')
  ).length;

  const newsCount = validAppearances.filter(
    (a) =>
      a.appearance_type === 'NEWS_ARTICLE' ||
      (a.sources?.[0]?.source_url || '').includes('news')
  ).length;

  // Filtered appearances based on active tab and search input
  const filteredAppearances = useMemo(() => {
    return validAppearances.filter((app) => {
      // 1. Media Type Filter
      if (activeMediaFilter === 'LINKEDIN') {
        const isLi =
          app.appearance_type === 'LINKEDIN_POST' ||
          app.appearance_type === 'ARTICLE' ||
          (app.sources?.[0]?.source_url || '').includes('linkedin.com');
        if (!isLi) return false;
      } else if (activeMediaFilter === 'INSTAGRAM') {
        const isIg =
          app.appearance_type === 'INSTAGRAM_POST' ||
          app.appearance_type === 'INSTAGRAM_REEL' ||
          (app.sources?.[0]?.source_url || '').includes('instagram.com');
        if (!isIg) return false;
      } else if (activeMediaFilter === 'YOUTUBE') {
        const isYt =
          app.appearance_type === 'PODCAST' ||
          app.appearance_type === 'INTERVIEW' ||
          (app.sources?.[0]?.source_url || '').includes('youtube.com');
        if (!isYt) return false;
      } else if (activeMediaFilter === 'NEWS') {
        const isNews =
          app.appearance_type === 'NEWS_ARTICLE' ||
          (app.sources?.[0]?.source_url || '').includes('news');
        if (!isNews) return false;
      }

      // 2. Search Query Filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = app.title?.toLowerCase().includes(q);
        const matchesDesc = app.description?.toLowerCase().includes(q);
        const matchesSummary = app.analysis?.summary?.toLowerCase().includes(q);
        if (!matchesTitle && !matchesDesc && !matchesSummary) return false;
      }

      return true;
    });
  }, [appearances, activeMediaFilter, searchQuery]);

  // Initials for avatar
  const initials = person?.name
    ? person.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* ============================================================== */}
      {/* 1. TARGET ACCOUNT HEADER & PROFILE DOSSIER                     */}
      {/* ============================================================== */}
      <div className="glass-panel rounded-2xl border border-slate-700/80 bg-gradient-to-b from-slate-900/90 via-slate-900/60 to-slate-950 overflow-hidden shadow-2xl relative">
        {/* Top Decorative Banner Strip */}
        <div className="h-28 sm:h-36 w-full bg-gradient-to-r from-blue-700/30 via-cyan-600/25 to-pink-600/25 relative border-b border-slate-800">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyan-500/10 via-transparent to-transparent" />
          <div className="absolute top-3 right-4 flex items-center gap-2">
            <span className="badge badge-verified shadow-md backdrop-blur-md">
              <ShieldCheck size={13} />
              <span>Verified Target</span>
            </span>
            <span className="text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
              ID: {person?.id?.slice(0, 8)}...
            </span>
          </div>
        </div>

        {/* Profile Identity Bar */}
        <div className="px-5 sm:px-8 pb-6 pt-0 relative flex flex-col md:flex-row md:items-end justify-between gap-6 -mt-12 sm:-mt-14">
          <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4 sm:gap-6">
            {/* Large Avatar Badge */}
            <div className="relative group shrink-0">
              <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 p-1 shadow-[0_0_30px_rgba(6,182,212,0.35)] border-4 border-slate-950">
                <div className="w-full h-full rounded-xl bg-slate-900 flex items-center justify-center text-2xl sm:text-3xl font-black tracking-wider text-cyan-300">
                  {initials}
                </div>
              </div>
              <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-emerald-500 border-2 border-slate-950 shadow-md">
                <CheckCircle2 size={15} className="text-white" />
              </div>
            </div>

            {/* Target Name, Designation & Social Links */}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-100">
                  {person?.name}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  Active Intelligence Subject
                </span>
              </div>

              <p className="text-sm font-semibold text-cyan-400 mt-1">
                {person?.profession || 'Professional / Executive'}
              </p>

              {/* Direct LinkedIn & Instagram Profile Links */}
              <div className="flex flex-wrap items-center gap-2.5 mt-2.5">
                {linkedinProfile ? (
                  <a
                    href={linkedinProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-[#0A66C2]/15 hover:bg-[#0A66C2]/25 text-[#38bdf8] border border-[#0A66C2]/40 transition-colors"
                  >
                    <span className="w-2 h-2 rounded-full bg-[#0A66C2]" />
                    <span>LinkedIn: @{linkedinProfile.username || 'profile'}</span>
                    <ExternalLink size={11} />
                  </a>
                ) : (
                  <span className="text-[11px] text-slate-500 flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded border border-slate-800">
                    <span>LinkedIn: Unlinked</span>
                  </span>
                )}

                {instagramProfile ? (
                  <a
                    href={instagramProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-pink-500/15 hover:bg-pink-500/25 text-pink-400 border border-pink-500/40 transition-colors"
                  >
                    <span className="w-2 h-2 rounded-full bg-pink-500" />
                    <span>Instagram: @{instagramProfile.username || 'profile'}</span>
                    <ExternalLink size={11} />
                  </a>
                ) : (
                  <span className="text-[11px] text-slate-500 flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded border border-slate-800">
                    <span>Instagram: Unlinked</span>
                  </span>
                )}

                {youtubeProfile && (
                  <a
                    href={youtubeProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-rose-500/15 hover:bg-rose-500/25 text-rose-400 border border-rose-500/40 transition-colors"
                  >
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span>YouTube: @{youtubeProfile.username || 'channel'}</span>
                    <ExternalLink size={11} />
                  </a>
                )}

                {otherProfiles.map((p) => (
                  <a
                    key={p.id}
                    href={p.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-900 text-slate-300 border border-slate-800 hover:text-cyan-400 transition-colors"
                  >
                    <Globe size={11} />
                    <span>{p.platform}</span>
                    <ExternalLink size={10} />
                  </a>
                ))}
              </div>
            </div>
          </div>

          {/* Action Buttons: Run Auto-Discovery & Analyze Link */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={onOpenUrlModal}
              className="btn btn-secondary text-xs px-3.5 py-2 border-cyan-500/40 text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20"
            >
              <Link2 size={14} />
              <span>Analyze Link</span>
            </button>

            <button
              onClick={onStartResearch}
              disabled={isResearching}
              className="btn btn-primary text-xs px-4 py-2 font-semibold shadow-lg shadow-cyan-500/20"
            >
              {isResearching ? (
                <>
                  <RotateCw size={14} className="animate-spin" />
                  <span>Searching Channels...</span>
                </>
              ) : (
                <>
                  <Play size={14} fill="white" />
                  <span>Run Auto-Discovery</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Biography & Description Callout Box */}
        <div className="px-5 sm:px-8 pb-6 pt-2 border-t border-slate-800/80">
          <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
              Account Description & Executive Bio
            </h4>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
              {person?.biography || (
                <span className="text-slate-500 italic">
                  No biography provided yet.
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* ============================================================== */}
      {/* 2. TARGET'S SOCIAL POSTS, ARTICLES & APPEARANCES FEED           */}
      {/* ============================================================== */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Layers size={18} className="text-cyan-400" />
              <span>Extracted Social Posts, Articles & Appearances</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {filteredAppearances.length} of {validAppearances.length} verified appearances
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search posts, captions, topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field text-xs pl-8 py-2 bg-slate-950/80"
            />
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-3 mb-4 scrollbar-none">
          {[
            { id: 'ALL', label: 'All Activity', count: validAppearances.length },
            { id: 'LINKEDIN', label: 'LinkedIn Posts & Articles', count: linkedinCount },
            { id: 'INSTAGRAM', label: 'Instagram Posts & Reels', count: instagramCount },
            { id: 'YOUTUBE', label: 'YouTube & Podcasts', count: youtubeCount },
            { id: 'NEWS', label: 'News Coverage', count: newsCount },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveMediaFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 border ${
                activeMediaFilter === tab.id
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  activeMediaFilter === tab.id
                    ? 'bg-cyan-400/30 text-white font-bold'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Content List */}
        {filteredAppearances.length === 0 ? (
          <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-800 bg-slate-950/30">
            <Sparkles size={28} className="mx-auto mb-2 text-slate-600" />
            <h4 className="text-sm font-semibold text-slate-300">No items match this filter</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {appearances.length === 0
                ? 'No appearances discovered yet. Click "Run Auto-Discovery" to collect posts and videos across the web.'
                : 'Try selecting a different filter or clearing your search keywords.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAppearances.map((item) => (
              <AppearanceCard
                key={item.id}
                item={item}
                onDelete={onDeleteAppearance}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
