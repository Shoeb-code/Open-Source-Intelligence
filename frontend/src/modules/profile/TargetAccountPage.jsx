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
  Building2
} from 'lucide-react';
import AppearanceCard from '../appearances/AppearanceCard';

export default function TargetAccountPage({
  person,
  appearances = [],
  onStartResearch,
  isResearching = false,
  onOpenUrlModal,
  onDeleteAppearance,
  onEnrichLinkedIn
}) {
  const [activeMediaFilter, setActiveMediaFilter] = useState('ALL'); // ALL, LINKEDIN, INSTAGRAM, YOUTUBE, NEWS
  const [searchQuery, setSearchQuery] = useState('');
  const [imgFailed, setImgFailed] = useState(false);

  // LinkedIn Enrichment UI states
  const [showEnrichModal, setShowEnrichModal] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [enrichFeedback, setEnrichFeedback] = useState(null); // { type: 'success'|'error', text: string }

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

  // Enriched collections (never assume arrays exist)
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

  // Initials for avatar fallback
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
        <div className="px-5 sm:px-8 pb-6 pt-0 relative flex flex-col xl:flex-row xl:items-end justify-between gap-6 -mt-12 sm:-mt-14">
          <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4 sm:gap-6 min-w-0">
            {/* Large Avatar Photo / Initials Badge */}
            <div className="relative group shrink-0">
              <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 p-1 shadow-[0_0_30px_rgba(6,182,212,0.35)] border-4 border-slate-950 overflow-hidden">
                {person?.profile_pic_url && !imgFailed ? (
                  <img
                    src={person.profile_pic_url}
                    alt={person?.name || 'Target Avatar'}
                    onError={() => setImgFailed(true)}
                    className="w-full h-full rounded-xl object-cover bg-slate-900"
                  />
                ) : (
                  <div className="w-full h-full rounded-xl bg-slate-900 flex items-center justify-center text-2xl sm:text-3xl font-black tracking-wider text-cyan-300">
                    {initials}
                  </div>
                )}
              </div>
              <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-emerald-500 border-2 border-slate-950 shadow-md">
                <CheckCircle2 size={15} className="text-white" />
              </div>
            </div>

            {/* Target Name, Headline, Metadata & Social Links */}
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
                {person?.headline || person?.profession || 'Professional / Executive'}
              </p>

              {/* Current Occupation, Location, Followers & Connections */}
              {(person?.occupation || person?.location || person?.follower_count != null || person?.connections != null) && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-2 text-xs text-slate-300">
                  {person?.occupation && (
                    <span className="inline-flex items-center gap-1.5">
                      <Briefcase size={13} className="text-cyan-400 shrink-0" />
                      <span>{person.occupation}</span>
                    </span>
                  )}
                  {person?.location && (
                    <span className="inline-flex items-center gap-1.5 text-slate-400">
                      <MapPin size={13} className="text-rose-400 shrink-0" />
                      <span>{person.location}</span>
                    </span>
                  )}
                  {(person?.follower_count != null || person?.connections != null) && (
                    <span className="inline-flex items-center gap-1.5 text-slate-400">
                      <Users size={13} className="text-blue-400 shrink-0" />
                      <span>
                        {person?.follower_count != null ? `${person.follower_count.toLocaleString()} followers` : ''}
                        {person?.follower_count != null && person?.connections != null ? ' • ' : ''}
                        {person?.connections != null ? `${person.connections}+ connections` : ''}
                      </span>
                    </span>
                  )}
                </div>
              )}

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

          {/* Action Buttons: Enrich LinkedIn Profile, Analyze Link & Auto-Discovery */}
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
              className="btn btn-secondary text-xs px-3.5 py-2 border-blue-500/40 text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 disabled:opacity-45 disabled:cursor-not-allowed"
            >
              {enriching ? (
                <>
                  <RotateCw size={14} className="animate-spin" />
                  <span>Enriching Profile...</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  <span>{isAlreadyEnriched ? 'Re-Enrich LinkedIn' : 'Enrich LinkedIn Profile'}</span>
                </>
              )}
            </button>

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

        {/* Enrichment Loading / Status Feedback Banners */}
        {enriching && (
          <div className="mx-5 sm:mx-8 mb-4 p-3 rounded-xl border border-blue-500/30 bg-blue-950/30 flex items-center gap-2.5 text-xs text-blue-300">
            <RotateCw size={15} className="animate-spin shrink-0" />
            <span>Querying Firecrawl Alexandria (EnrichLayer) for verified LinkedIn career and education records...</span>
          </div>
        )}

        {enrichFeedback && (
          <div
            className={`mx-5 sm:mx-8 mb-4 p-3 rounded-xl border flex items-center justify-between gap-3 text-xs ${
              enrichFeedback.type === 'success'
                ? 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300'
                : 'border-rose-500/30 bg-rose-950/30 text-rose-300'
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
              className="text-slate-400 hover:text-slate-200 p-0.5"
              aria-label="Dismiss status notice"
            >
              <X size={14} />
            </button>
          </div>
        )}

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
      {/* 2. PROFESSIONAL PROFILE SECTION (ALEXANDRIA ENRICHLAYER)        */}
      {/* ============================================================== */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Briefcase size={18} className="text-blue-400" />
              <span>Professional Profile</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {isAlreadyEnriched
                ? `Structured LinkedIn career, education, and project records • Enriched ${new Date(
                    person.profile_enriched_at
                  ).toLocaleDateString()}`
                : 'Verified LinkedIn career background, education, and summary powered by Firecrawl Alexandria (EnrichLayer)'}
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
          <div className="text-center py-10 px-4 rounded-xl border border-dashed border-slate-800 bg-slate-950/30">
            <Briefcase size={26} className="mx-auto mb-2 text-slate-600" />
            <h4 className="text-sm font-semibold text-slate-300">
              {isAlreadyEnriched
                ? 'Professional profile details are unavailable in the public LinkedIn record'
                : 'LinkedIn profile has not been enriched yet'}
            </h4>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
              {hasVerifiedLinkedIn
                ? 'Click "Enrich LinkedIn Profile" above to fetch work experience, education, projects, and summary (uses 10 Firecrawl credits).'
                : 'Run Auto-Discovery first so the target’s LinkedIn /in/ profile URL is verified before enrichment.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {/* Professional Summary */}
            {person?.summary && (
              <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800/90">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                  Professional Summary
                </h4>
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                  {person.summary}
                </p>
              </div>
            )}

            {/* Work Experience Timeline */}
            {experiences.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Building2 size={14} className="text-cyan-400" />
                  <span>Work Experience ({experiences.length})</span>
                </h4>
                <div className="relative pl-4 sm:pl-5 border-l-2 border-slate-800 space-y-4">
                  {experiences.map((exp, idx) => (
                    <div
                      key={`${exp.company}-${exp.title}-${idx}`}
                      className="relative bg-slate-950/50 rounded-xl p-4 border border-slate-800/80 hover:border-slate-700 transition-colors"
                    >
                      <span
                        className={`absolute -left-[23px] sm:-left-[27px] top-5 w-3 h-3 rounded-full border-2 border-slate-950 ${
                          exp.is_current ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-cyan-500'
                        }`}
                      />
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                        <div>
                          <h5 className="text-sm font-bold text-slate-100">
                            {exp.title || 'Role'}
                          </h5>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-cyan-400 font-medium mt-0.5">
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
                              <span className="text-slate-400 font-normal">• {exp.location}</span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {exp.is_current && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                              Current
                            </span>
                          )}
                          {(exp.start_date || exp.end_date) && (
                            <span className="text-xs font-mono text-slate-400">
                              {exp.start_date || '?'} — {exp.end_date || 'Present'}
                            </span>
                          )}
                        </div>
                      </div>

                      {exp.description && (
                        <p className="text-xs text-slate-300 mt-2 leading-relaxed whitespace-pre-line">
                          {exp.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education & Projects 2-Column Grid when both present */}
            {(education.length > 0 || projects.length > 0) && (
              <div className={`grid grid-cols-1 ${education.length > 0 && projects.length > 0 ? 'lg:grid-cols-2' : ''} gap-5`}>
                {education.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <GraduationCap size={15} className="text-indigo-400" />
                      <span>Education ({education.length})</span>
                    </h4>
                    <div className="space-y-3">
                      {education.map((edu, idx) => (
                        <div
                          key={`${edu.school}-${idx}`}
                          className="bg-slate-950/50 rounded-xl p-3.5 border border-slate-800/80"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h5 className="text-sm font-semibold text-slate-100">
                                {edu.school || 'Institution'}
                              </h5>
                              {(edu.degree_name || edu.field_of_study) && (
                                <p className="text-xs text-indigo-300 mt-0.5 font-medium">
                                  {[edu.degree_name, edu.field_of_study].filter(Boolean).join(' • ')}
                                </p>
                              )}
                            </div>
                            {(edu.start_date || edu.end_date) && (
                              <span className="text-[11px] font-mono text-slate-400 shrink-0">
                                {[edu.start_date, edu.end_date].filter(Boolean).join(' — ')}
                              </span>
                            )}
                          </div>
                          {edu.description && (
                            <p className="text-xs text-slate-400 mt-1.5">{edu.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {projects.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <FolderKanban size={15} className="text-amber-400" />
                      <span>Projects & Initiatives ({projects.length})</span>
                    </h4>
                    <div className="space-y-3">
                      {projects.map((proj, idx) => (
                        <div
                          key={`${proj.title}-${idx}`}
                          className="bg-slate-950/50 rounded-xl p-3.5 border border-slate-800/80"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="text-sm font-semibold text-slate-100">
                              {proj.title || 'Project'}
                            </h5>
                            {proj.url && (
                              <a
                                href={proj.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1 text-xs shrink-0"
                              >
                                <span>Link</span>
                                <ExternalLink size={11} />
                              </a>
                            )}
                          </div>
                          {proj.description && (
                            <p className="text-xs text-slate-300 mt-1 leading-relaxed">{proj.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Skills & Certifications (Rendered ONLY when available) */}
            {(skills.length > 0 || certifications.length > 0) && (
              <div className="flex flex-col gap-4 pt-2 border-t border-slate-800/80">
                {skills.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                      <Award size={14} className="text-emerald-400" />
                      <span>Skills ({skills.length})</span>
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {skills.map((skill, idx) => (
                        <span
                          key={`${skill}-${idx}`}
                          className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-950 text-slate-200 border border-slate-800"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {certifications.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                      Certifications ({certifications.length})
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {certifications.map((cert, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-950/50 rounded-lg p-3 border border-slate-800 text-xs text-slate-200"
                        >
                          <div className="font-semibold">{cert.name || cert.title || 'Certification'}</div>
                          {cert.authority && <div className="text-slate-400 mt-0.5">{cert.authority}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Informative note for missing optional sections without cluttering UI with empty boxes */}
            {unavailableFields.length > 0 && (
              <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-800/60">
                Unavailable in public LinkedIn record: {unavailableFields.join(', ')}.
              </p>
            )}
          </div>
        )}
      </div>

      {/* ============================================================== */}
      {/* 3. TARGET'S SOCIAL POSTS, ARTICLES & APPEARANCES FEED           */}
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

      {/* ============================================================== */}
      {/* CONFIRMATION MODAL FOR 10-CREDIT ALEXANDRIA ENRICHMENT         */}
      {/* ============================================================== */}
      {showEnrichModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="enrich-modal-title"
        >
          <div className="glass-panel max-w-md w-full rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-blue-500/15 text-blue-400 border border-blue-500/30">
                  <Sparkles size={18} />
                </div>
                <h3 id="enrich-modal-title" className="text-base font-bold text-slate-100">
                  Confirm LinkedIn Profile Enrichment
                </h3>
              </div>
              <button
                onClick={() => setShowEnrichModal(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
                aria-label="Close confirmation dialog"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed mb-5">
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
