import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  ExternalLink,
  Play,
  RotateCw,
  Search,
  CheckCircle2,
  Layers,
  Sparkles,
  Link2,
  Globe,
  Briefcase,
  GraduationCap,
  MapPin,
  Users,
  FolderKanban,
  Award,
  AlertCircle,
  X,
  Building2,
  User
} from 'lucide-react';
import AppearanceCard from '../appearances/AppearanceCard';
import AIInsightsPanel from './AIInsightsPanel';

export default function TargetAccountPage({
  person,
  appearances = [],
  sources = [],
  insightsHistory = null,
  onStartResearch,
  isResearching = false,
  onOpenUrlModal,
  onDeleteAppearance,
  onEnrichLinkedIn,
  onGenerateInsights
}) {
  const [sectionTab, setSectionTab] = useState('profile'); // 'profile' | 'ai_insights'
  const [activeMediaFilter, setActiveMediaFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [imgFailed, setImgFailed] = useState(false);

  // LinkedIn Enrichment UI states
  const [showEnrichModal, setShowEnrichModal] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [enrichFeedback, setEnrichFeedback] = useState(null);

  // Extract Social Profiles
  const linkedinProfile = person?.social_profiles?.find((p) => p.platform === 'linkedin');
  const instagramProfile = person?.social_profiles?.find((p) => p.platform === 'instagram');
  const youtubeProfile = person?.social_profiles?.find((p) => p.platform === 'youtube');
  const otherProfiles = person?.social_profiles?.filter(
    (p) => !['linkedin', 'instagram', 'youtube'].includes(p.platform)
  ) || [];

  const hasVerifiedLinkedIn = Boolean(
    linkedinProfile &&
      linkedinProfile.verification_status === 'VERIFIED' &&
      (linkedinProfile.profile_url || '').toLowerCase().includes('/in/')
  );

  const isAlreadyEnriched = Boolean(
    person?.enrichment_status === 'SUCCESS' && person?.profile_enriched_at
  );

  async function handleConfirmEnrich() {
    if (!person?.id || !onEnrichLinkedIn || enriching) return;
    setShowEnrichModal(false);
    setEnriching(true);
    setEnrichFeedback(null);
    try {
      const res = await onEnrichLinkedIn(person.id, isAlreadyEnriched);
      setEnrichFeedback({
        type: 'success',
        text: `${res?.message || 'LinkedIn profile enriched successfully.'} (Credits used: ${res?.credits_cost ?? 0})`
      });
    } catch (err) {
      setEnrichFeedback({
        type: 'error',
        text: err.message || 'Failed to enrich LinkedIn profile.'
      });
    } finally {
      setEnriching(false);
    }
  }

  // Enriched collections
  const experiences = Array.isArray(person?.experiences) ? person.experiences : [];
  const education = Array.isArray(person?.education) ? person.education : [];
  const projects = Array.isArray(person?.projects) ? person.projects : [];
  const skills = Array.isArray(person?.skills) ? person.skills : [];
  const certifications = Array.isArray(person?.certifications) ? person.certifications : [];

  const hasAnyEnrichedData = Boolean(
    person?.headline ||
      person?.summary ||
      experiences.length > 0 ||
      education.length > 0 ||
      projects.length > 0 ||
      skills.length > 0 ||
      certifications.length > 0
  );

  const unavailableFields = useMemo(() => {
    if (!isAlreadyEnriched) return [];
    const missing = [];
    if (!person?.summary) missing.push('Professional Summary');
    if (experiences.length === 0) missing.push('Work Experience');
    if (education.length === 0) missing.push('Education');
    if (projects.length === 0) missing.push('Projects');
    if (skills.length === 0) missing.push('Skills');
    if (certifications.length === 0) missing.push('Certifications');
    return missing;
  }, [isAlreadyEnriched, person?.summary, experiences.length, education.length, projects.length, skills.length, certifications.length]);

  const validAppearances = useMemo(() => {
    return appearances.filter((a) => a.identity_status !== 'REJECTED');
  }, [appearances]);

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

  const filteredAppearances = useMemo(() => {
    return validAppearances.filter((app) => {
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

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = app.title?.toLowerCase().includes(q);
        const matchesDesc = app.description?.toLowerCase().includes(q);
        const matchesSummary = app.analysis?.summary?.toLowerCase().includes(q);
        if (!matchesTitle && !matchesDesc && !matchesSummary) return false;
      }

      return true;
    });
  }, [validAppearances, activeMediaFilter, searchQuery]);

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
      {/* 1. CLEAN TARGET ACCOUNT HEADER CARD (WHITE LIGHT UI)           */}
      {/* ============================================================== */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        {/* Soft Clean Banner */}
        <div className="h-24 sm:h-28 w-full bg-gradient-to-r from-blue-50 via-sky-50 to-indigo-50 relative border-b border-slate-200">
          <div className="absolute top-3 right-4 flex items-center gap-2">
            <span className="badge badge-verified">
              <ShieldCheck size={13} />
              <span>Verified Person</span>
            </span>
          </div>
        </div>

        {/* Profile Identity Row */}
        <div className="px-5 sm:px-8 pb-6 pt-0 relative flex flex-col xl:flex-row xl:items-end justify-between gap-6 -mt-12">
          <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4 sm:gap-5 min-w-0">
            {/* Avatar Photo or Initials */}
            <div className="relative shrink-0">
              <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl bg-white p-1 shadow-md border border-slate-200 overflow-hidden">
                {person?.profile_pic_url && !imgFailed ? (
                  <img
                    src={person.profile_pic_url}
                    alt={person?.name || 'Target Avatar'}
                    onError={() => setImgFailed(true)}
                    className="w-full h-full rounded-xl object-cover bg-slate-100"
                  />
                ) : (
                  <div className="w-full h-full rounded-xl bg-blue-50 flex items-center justify-center text-2xl sm:text-3xl font-bold text-blue-700">
                    {initials}
                  </div>
                )}
              </div>
              <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-emerald-600 border-2 border-white shadow">
                <CheckCircle2 size={14} className="text-white" />
              </div>
            </div>

            {/* Name, Headline, Metadata & Links */}
            <div className="min-w-0 pt-2 sm:pt-0">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                {person?.name}
              </h1>

              <p className="text-sm font-semibold text-blue-700 mt-1">
                {person?.headline || person?.profession || 'Professional / Executive'}
              </p>

              {(person?.occupation || person?.location || person?.follower_count != null || person?.connections != null) && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-2 text-xs text-slate-600">
                  {person?.occupation && (
                    <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                      <Briefcase size={13} className="text-blue-600 shrink-0" />
                      <span>{person.occupation}</span>
                    </span>
                  )}
                  {person?.location && (
                    <span className="inline-flex items-center gap-1.5">
                      <MapPin size={13} className="text-rose-500 shrink-0" />
                      <span>{person.location}</span>
                    </span>
                  )}
                  {(person?.follower_count != null || person?.connections != null) && (
                    <span className="inline-flex items-center gap-1.5">
                      <Users size={13} className="text-slate-500 shrink-0" />
                      <span>
                        {person?.follower_count != null ? `${person.follower_count.toLocaleString()} followers` : ''}
                        {person?.follower_count != null && person?.connections != null ? ' • ' : ''}
                        {person?.connections != null ? `${person.connections}+ connections` : ''}
                      </span>
                    </span>
                  )}
                </div>
              )}

              {/* Direct Profile Links */}
              <div className="flex flex-wrap items-center gap-2 mt-3">
                {linkedinProfile ? (
                  <a
                    href={linkedinProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-blue-50 hover:bg-blue-100 text-[#0A66C2] border border-blue-200 transition-colors"
                  >
                    <span className="w-2 h-2 rounded-full bg-[#0A66C2]" />
                    <span>LinkedIn: @{linkedinProfile.username || 'profile'}</span>
                    <ExternalLink size={11} />
                  </a>
                ) : (
                  <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                    LinkedIn: Not linked
                  </span>
                )}

                {instagramProfile ? (
                  <a
                    href={instagramProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-pink-50 hover:bg-pink-100 text-pink-700 border border-pink-200 transition-colors"
                  >
                    <span className="w-2 h-2 rounded-full bg-pink-500" />
                    <span>Instagram: @{instagramProfile.username || 'profile'}</span>
                    <ExternalLink size={11} />
                  </a>
                ) : (
                  <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                    Instagram: Not linked
                  </span>
                )}

                {youtubeProfile && (
                  <a
                    href={youtubeProfile.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 transition-colors"
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
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-50 text-slate-700 border border-slate-200 hover:border-blue-300 hover:text-blue-700 transition-colors"
                  >
                    <Globe size={11} />
                    <span>{p.platform}</span>
                    <ExternalLink size={10} />
                  </a>
                ))}
              </div>
            </div>
          </div>

          {/* Primary Simple Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={() => setShowEnrichModal(true)}
              disabled={enriching || !hasVerifiedLinkedIn}
              title={
                !hasVerifiedLinkedIn
                  ? 'Run Auto-Discovery first to verify a LinkedIn /in/ profile URL'
                  : isAlreadyEnriched
                  ? 'Re-fetch latest LinkedIn education & experience (10 Firecrawl credits)'
                  : 'Extract LinkedIn experience, education & summary (10 Firecrawl credits)'
              }
              className="btn btn-secondary text-xs px-3.5 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {enriching ? (
                <>
                  <RotateCw size={14} className="animate-spin" />
                  <span>Enriching Profile...</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} className="text-blue-600" />
                  <span>{isAlreadyEnriched ? 'Re-Enrich LinkedIn' : 'Enrich LinkedIn Profile'}</span>
                </>
              )}
            </button>

            <button
              onClick={onOpenUrlModal}
              className="btn btn-secondary text-xs px-3.5 py-2"
            >
              <Link2 size={14} className="text-slate-600" />
              <span>Add a Link</span>
            </button>

            <button
              onClick={onStartResearch}
              disabled={isResearching}
              className="btn btn-primary text-xs px-4 py-2"
            >
              {isResearching ? (
                <>
                  <RotateCw size={14} className="animate-spin" />
                  <span>Searching Web...</span>
                </>
              ) : (
                <>
                  <Play size={14} fill="white" />
                  <span>Search Web & Social</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Enrichment Loading / Status Feedback Banners */}
        {enriching && (
          <div className="mx-5 sm:mx-8 mb-4 p-3 rounded-xl border border-blue-200 bg-blue-50 flex items-center gap-2.5 text-xs text-blue-800">
            <RotateCw size={15} className="animate-spin shrink-0" />
            <span>Querying Firecrawl Alexandria (EnrichLayer) for verified LinkedIn career and education records...</span>
          </div>
        )}

        {enrichFeedback && (
          <div
            className={`mx-5 sm:mx-8 mb-4 p-3 rounded-xl border flex items-center justify-between gap-3 text-xs ${
              enrichFeedback.type === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                : 'border-rose-200 bg-rose-50 text-rose-800'
            }`}
          >
            <div className="flex items-center gap-2">
              {enrichFeedback.type === 'success' ? (
                <CheckCircle2 size={15} className="shrink-0" />
              ) : (
                <AlertCircle size={15} className="shrink-0" />
              )}
              <span>{enrichFeedback.text}</span>
            </div>
            <button
              onClick={() => setEnrichFeedback(null)}
              className="text-slate-500 hover:text-slate-800 p-0.5"
              aria-label="Dismiss status notice"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Executive Bio */}
        <div className="px-5 sm:px-8 pb-6 pt-3 border-t border-slate-100">
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              About This Person
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed">
              {person?.biography || (
                <span className="text-slate-400 italic">No description added yet.</span>
              )}
            </p>
          </div>
        </div>

        {/* Simple Two-Tab Switch inside TargetAccountPage: Profile vs AI Insights */}
        <div className="px-5 sm:px-8 border-t border-slate-200 bg-slate-50/70 flex items-center gap-2">
          <button
            onClick={() => setSectionTab('profile')}
            className={`py-3 px-4 text-xs sm:text-sm font-semibold border-b-2 inline-flex items-center gap-2 transition-colors ${
              sectionTab === 'profile'
                ? 'border-blue-600 text-blue-700 bg-white'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <User size={15} />
            <span>Profile & Public Appearances</span>
          </button>

          <button
            onClick={() => setSectionTab('ai_insights')}
            className={`py-3 px-4 text-xs sm:text-sm font-semibold border-b-2 inline-flex items-center gap-2 transition-colors ${
              sectionTab === 'ai_insights'
                ? 'border-blue-600 text-blue-700 bg-white'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles size={15} />
            <span>AI Insights</span>
            {insightsHistory?.history?.length > 0 && (
              <span className="text-[11px] px-1.5 py-0.2 rounded-full bg-blue-100 text-blue-700 font-bold">
                {insightsHistory.history.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ============================================================== */}
      {/* TAB VIEW 1: AI INSIGHTS GENERATOR                              */}
      {/* ============================================================== */}
      {sectionTab === 'ai_insights' ? (
        <AIInsightsPanel
          person={person}
          personName={person?.name}
          appearances={appearances}
          sources={sources}
          insightsHistory={insightsHistory}
          onGenerateInsights={(focusNotes) => onGenerateInsights && onGenerateInsights(person.id, focusNotes)}
        />
      ) : (
        <>
          {/* ============================================================== */}
          {/* 2. PROFESSIONAL PROFILE SECTION                                */}
          {/* ============================================================== */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Briefcase size={18} className="text-blue-600" />
                  <span>Professional Profile</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {isAlreadyEnriched
                    ? `Work history, education & projects • Last updated ${new Date(
                        person.profile_enriched_at
                      ).toLocaleDateString()}`
                    : 'Career history, education, and summary from verified LinkedIn profile data'}
                </p>
              </div>

              {isAlreadyEnriched && (
                <span className="badge badge-verified self-start sm:self-center">
                  <CheckCircle2 size={12} />
                  <span>LinkedIn Enriched</span>
                </span>
              )}
            </div>

            {!hasAnyEnrichedData ? (
              <div className="text-center py-10 px-4 rounded-xl border border-dashed border-slate-300 bg-slate-50">
                <Briefcase size={26} className="mx-auto mb-2 text-slate-400" />
                <h4 className="text-sm font-semibold text-slate-800">
                  {isAlreadyEnriched
                    ? 'Professional profile details are unavailable in the public LinkedIn record'
                    : 'LinkedIn profile has not been enriched yet'}
                </h4>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
                  {hasVerifiedLinkedIn
                    ? 'Click "Enrich LinkedIn Profile" above to fetch work experience, education, projects, and summary (uses 10 Firecrawl credits).'
                    : 'Click "Search Web & Social" first so a verified LinkedIn profile URL can be discovered.'}
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {person?.summary && (
                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Professional Summary
                    </h4>
                    <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                      {person.summary}
                    </p>
                  </div>
                )}

                {experiences.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <Building2 size={14} className="text-blue-600" />
                      <span>Work Experience ({experiences.length})</span>
                    </h4>
                    <div className="relative pl-4 sm:pl-5 border-l-2 border-slate-200 space-y-4">
                      {experiences.map((exp, idx) => (
                        <div
                          key={`${exp.company}-${exp.title}-${idx}`}
                          className="relative bg-slate-50 rounded-xl p-4 border border-slate-200 hover:border-slate-300 transition-colors"
                        >
                          <span
                            className={`absolute -left-[23px] sm:-left-[27px] top-5 w-3 h-3 rounded-full border-2 border-white ${
                              exp.is_current ? 'bg-emerald-500' : 'bg-blue-500'
                            }`}
                          />
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                            <div>
                              <h5 className="text-sm font-bold text-slate-900">
                                {exp.title || 'Role'}
                              </h5>
                              <div className="flex flex-wrap items-center gap-2 text-xs text-blue-700 font-medium mt-0.5">
                                {exp.company_linkedin_profile_url ? (
                                  <a
                                    href={exp.company_linkedin_profile_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="hover:underline inline-flex items-center gap-1"
                                  >
                                    <span>{exp.company}</span>
                                    <ExternalLink size={10} />
                                  </a>
                                ) : (
                                  <span>{exp.company}</span>
                                )}
                                {exp.location && (
                                  <span className="text-slate-500 font-normal">• {exp.location}</span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              {exp.is_current && (
                                <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Current
                                </span>
                              )}
                              {(exp.start_date || exp.end_date) && (
                                <span className="text-xs font-mono text-slate-500">
                                  {exp.start_date || '?'} — {exp.end_date || 'Present'}
                                </span>
                              )}
                            </div>
                          </div>

                          {exp.description && (
                            <p className="text-xs text-slate-600 mt-2 leading-relaxed whitespace-pre-line">
                              {exp.description}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(education.length > 0 || projects.length > 0) && (
                  <div className={`grid grid-cols-1 ${education.length > 0 && projects.length > 0 ? 'lg:grid-cols-2' : ''} gap-5`}>
                    {education.length > 0 && (
                      <div>
                        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                          <GraduationCap size={15} className="text-indigo-600" />
                          <span>Education ({education.length})</span>
                        </h4>
                        <div className="space-y-3">
                          {education.map((edu, idx) => (
                            <div
                              key={`${edu.school}-${idx}`}
                              className="bg-slate-50 rounded-xl p-3.5 border border-slate-200"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <h5 className="text-sm font-semibold text-slate-900">
                                    {edu.school || 'Institution'}
                                  </h5>
                                  {(edu.degree_name || edu.field_of_study) && (
                                    <p className="text-xs text-indigo-700 mt-0.5 font-medium">
                                      {[edu.degree_name, edu.field_of_study].filter(Boolean).join(' • ')}
                                    </p>
                                  )}
                                </div>
                                {(edu.start_date || edu.end_date) && (
                                  <span className="text-[11px] font-mono text-slate-500 shrink-0">
                                    {[edu.start_date, edu.end_date].filter(Boolean).join(' — ')}
                                  </span>
                                )}
                              </div>
                              {edu.description && (
                                <p className="text-xs text-slate-600 mt-1.5">{edu.description}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {projects.length > 0 && (
                      <div>
                        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                          <FolderKanban size={15} className="text-amber-600" />
                          <span>Projects & Initiatives ({projects.length})</span>
                        </h4>
                        <div className="space-y-3">
                          {projects.map((proj, idx) => (
                            <div
                              key={`${proj.title}-${idx}`}
                              className="bg-slate-50 rounded-xl p-3.5 border border-slate-200"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <h5 className="text-sm font-semibold text-slate-900">
                                  {proj.title || 'Project'}
                                </h5>
                                {proj.url && (
                                  <a
                                    href={proj.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 text-xs shrink-0"
                                  >
                                    <span>Link</span>
                                    <ExternalLink size={11} />
                                  </a>
                                )}
                              </div>
                              {proj.description && (
                                <p className="text-xs text-slate-600 mt-1 leading-relaxed">{proj.description}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {(skills.length > 0 || certifications.length > 0) && (
                  <div className="flex flex-col gap-4 pt-2 border-t border-slate-200">
                    {skills.length > 0 && (
                      <div>
                        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                          <Award size={14} className="text-emerald-600" />
                          <span>Skills ({skills.length})</span>
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {skills.map((skill, idx) => (
                            <span
                              key={`${skill}-${idx}`}
                              className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-50 text-slate-800 border border-slate-200"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {certifications.length > 0 && (
                      <div>
                        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">
                          Certifications ({certifications.length})
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          {certifications.map((cert, idx) => (
                            <div
                              key={idx}
                              className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs text-slate-800"
                            >
                              <div className="font-semibold">{cert.name || cert.title || 'Certification'}</div>
                              {cert.authority && <div className="text-slate-500 mt-0.5">{cert.authority}</div>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {unavailableFields.length > 0 && (
                  <p className="text-xs text-slate-500 pt-2 border-t border-slate-100">
                    Unavailable in public LinkedIn record: {unavailableFields.join(', ')}.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* ============================================================== */}
          {/* 3. SOCIAL POSTS, ARTICLES & APPEARANCES FEED                   */}
          {/* ============================================================== */}
          <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Layers size={18} className="text-blue-600" />
                  <span>Public Posts, Videos & Articles</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Showing {filteredAppearances.length} of {validAppearances.length} verified items
                </p>
              </div>

              <div className="relative w-full sm:w-72">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter posts, videos, topics..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="input-field text-xs pl-8 py-2"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-3 mb-4">
              {[
                { id: 'ALL', label: 'All Activity', count: validAppearances.length },
                { id: 'LINKEDIN', label: 'LinkedIn', count: linkedinCount },
                { id: 'INSTAGRAM', label: 'Instagram', count: instagramCount },
                { id: 'YOUTUBE', label: 'YouTube & Podcasts', count: youtubeCount },
                { id: 'NEWS', label: 'News Articles', count: newsCount },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveMediaFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 border ${
                    activeMediaFilter === tab.id
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      activeMediaFilter === tab.id
                        ? 'bg-blue-600 text-white font-bold'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {filteredAppearances.length === 0 ? (
              <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-300 bg-slate-50">
                <Sparkles size={28} className="mx-auto mb-2 text-slate-400" />
                <h4 className="text-sm font-semibold text-slate-800">No items match this filter</h4>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  {appearances.length === 0
                    ? 'No appearances discovered yet. Click "Search Web & Social" to collect posts and videos.'
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
        </>
      )}

      {/* Confirmation Modal for LinkedIn Enrichment */}
      {showEnrichModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="enrich-modal-title"
        >
          <div className="bg-white max-w-md w-full rounded-2xl border border-slate-200 p-6 shadow-xl">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-200">
                  <Sparkles size={18} />
                </div>
                <h3 id="enrich-modal-title" className="text-base font-bold text-slate-900">
                  Confirm LinkedIn Profile Enrichment
                </h3>
              </div>
              <button
                onClick={() => setShowEnrichModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-100"
                aria-label="Close confirmation dialog"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed mb-5">
              Enriching this profile will consume 10 Firecrawl credits. Do you want to continue?
            </p>

            <div className="flex items-center justify-end gap-2.5">
              <button
                onClick={() => setShowEnrichModal(false)}
                className="btn btn-secondary text-xs px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmEnrich}
                className="btn btn-primary text-xs px-4 py-2 font-semibold"
              >
                Continue & Enrich
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
