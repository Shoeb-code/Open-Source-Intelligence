import React, { useState, useEffect } from 'react';
import {
  Radar,
  Play,
  RotateCw,
  ExternalLink,
  ShieldCheck,
  FileText,
  Layers,
  Calendar,
  Globe,
  PlusCircle,
  Activity,
  Link2,
  Sparkles,
  ArrowRight,
  Search,
  CheckCircle2,
  Menu
} from 'lucide-react';
import { api } from './api';

// Feature Modules
import TargetSelector from './modules/identity/TargetSelector';
import RegisterTargetModal from './modules/identity/RegisterTargetModal';
import UrlUploadModal from './modules/ingestion/UrlUploadModal';
import MetricsGrid from './modules/overview/MetricsGrid';
import TopicCloud from './modules/overview/TopicCloud';
import EvidenceQuotes from './modules/overview/EvidenceQuotes';
import AppearanceList from './modules/appearances/AppearanceList';
import TimelineView from './modules/timeline/TimelineView';
import SourcesTable from './modules/sources/SourcesTable';

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [persons, setPersons] = useState([]);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);

  // Active Research State
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [isResearching, setIsResearching] = useState(false);

  // Active Tab
  const [activeTab, setActiveTab] = useState('overview'); // overview, appearances, timeline, sources

  // Intelligence Data
  const [reportData, setReportData] = useState(null);
  const [appearances, setAppearances] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sources, setSources] = useState([]);
  const [loadingData, setLoadingData] = useState(false);

  // Modal States
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showUrlUploadModal, setShowUrlUploadModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // 1. Initial Load & Backend Health
  useEffect(() => {
    checkHealthAndLoad();
    const interval = setInterval(checkHealthAndLoad, 15000);
    return () => clearInterval(interval);
  }, []);

  async function checkHealthAndLoad() {
    try {
      const isUp = await api.checkHealth();
      setBackendOnline(isUp);
      await loadPersons();
    } catch {
      setBackendOnline(false);
    }
  }

  async function loadPersons() {
    try {
      const list = await api.getPersons();
      setPersons(list);
      setBackendOnline(true);
      if (list.length > 0 && !selectedPersonId) {
        setSelectedPersonId(list[0].id);
      }
    } catch (err) {
      console.error('Error loading persons:', err);
    }
  }

  // 2. Load Selected Target Data
  useEffect(() => {
    if (!selectedPersonId) {
      setSelectedPerson(null);
      setReportData(null);
      setAppearances([]);
      setTimeline([]);
      setSources([]);
      return;
    }
    const found = persons.find((p) => p.id === selectedPersonId);
    setSelectedPerson(found || null);
    fetchPersonIntelligence(selectedPersonId);
  }, [selectedPersonId, persons]);

  async function fetchPersonIntelligence(personId) {
    setLoadingData(true);
    try {
      const [rep, apps, tm, srcs] = await Promise.allSettled([
        api.getReport(personId),
        api.getAppearances(personId),
        api.getTimeline(personId),
        api.getSources(personId),
      ]);

      if (rep.status === 'fulfilled') setReportData(rep.value);
      if (apps.status === 'fulfilled') setAppearances(apps.value);
      if (tm.status === 'fulfilled') setTimeline(tm.value);
      if (srcs.status === 'fulfilled') setSources(srcs.value);
    } catch (err) {
      console.error('Error loading person intelligence:', err);
    } finally {
      setLoadingData(false);
    }
  }

  // 3. Trigger Discovery Pipeline
  async function handleStartResearch() {
    if (!selectedPersonId || isResearching) return;
    try {
      setIsResearching(true);
      const res = await api.startResearch(selectedPersonId);
      setActiveJobId(res.id);
      setJobStatus(res);
    } catch (err) {
      alert(`Failed to start research: ${err.message}`);
      setIsResearching(false);
    }
  }

  // 4. Poll Research Progress
  useEffect(() => {
    if (!activeJobId || !isResearching) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getResearchStatus(activeJobId);
        setJobStatus(status);

        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          setIsResearching(false);
          setActiveJobId(null);
          fetchPersonIntelligence(selectedPersonId);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [activeJobId, isResearching, selectedPersonId]);

  // 5. Delete Person
  async function handleDeletePerson(personId) {
    try {
      await api.deletePerson(personId);
      setPersons((prev) => prev.filter((p) => p.id !== personId));
      if (selectedPersonId === personId) {
        const remaining = persons.filter((p) => p.id !== personId);
        setSelectedPersonId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err) {
      alert(`Failed to delete target: ${err.message}`);
    }
  }

  // 6. Delete Appearance
  async function handleDeleteAppearance(appearanceId) {
    if (!selectedPersonId) return;
    try {
      await api.deleteAppearance(selectedPersonId, appearanceId);
      setAppearances((prev) => prev.filter((a) => a.id !== appearanceId));
      fetchPersonIntelligence(selectedPersonId);
    } catch (err) {
      alert(`Failed to delete appearance: ${err.message}`);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans">
      {/* --- TOP NAVBAR --- */}
      <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur-md sticky top-0 z-40 px-3.5 sm:px-6 py-3 sm:py-3.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          {/* Mobile Drawer Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden p-2 rounded-xl border border-slate-800 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
            title="Open Target Profiles"
            aria-label="Open Target Profiles"
          >
            <Menu size={20} />
          </button>

          <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-[0_0_18px_rgba(6,182,212,0.4)] shrink-0">
            <Radar size={20} className="text-white sm:w-[22px] sm:h-[22px]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-bold tracking-tight text-slate-100 truncate">
              PUBLIC APPEARANCE <span className="text-cyan-400">INTELLIGENCE</span>
            </h1>
            <p className="text-[11px] sm:text-xs text-slate-400 truncate hidden xs:block">
              Search & Analyze Public Interviews, Podcasts, Talks & Articles
            </p>
          </div>
        </div>

        {/* Backend Status Pill & Links */}
        <div className="flex items-center gap-2 sm:gap-4 shrink-0">
          <div
            className={`inline-flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-semibold tracking-wide border ${
              backendOnline
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-rose-500'
              }`}
            />
            <span className="hidden sm:inline">
              {backendOnline ? 'System Online (Port 8000)' : 'Connecting to Server...'}
            </span>
            <span className="sm:hidden">{backendOnline ? 'Online' : 'Connecting...'}</span>
          </div>

          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors inline-flex items-center gap-1"
          >
            <span className="hidden sm:inline">API Docs</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </header>

      {/* --- MAIN LAYOUT --- */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* --- MODULE 1: TARGET SELECTOR SIDEBAR --- */}
        <TargetSelector
          persons={persons}
          selectedPersonId={selectedPersonId}
          onSelectPerson={setSelectedPersonId}
          onOpenRegisterModal={() => setShowRegisterModal(true)}
          onDeletePerson={handleDeletePerson}
          mobileOpen={mobileMenuOpen}
          onCloseMobile={() => setMobileMenuOpen(false)}
        />

        {/* --- MAIN INTELLIGENCE DASHBOARD --- */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-slate-950">
          {selectedPerson ? (
            <>
              {/* --- TARGET HEADER & CONTROL BAR --- */}
              <div className="p-4 sm:p-6 border-b border-slate-800 bg-slate-900/40 backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-4 sm:gap-6">
                <div>
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-100">{selectedPerson.name}</h2>
                    <span className="badge badge-verified">
                      <ShieldCheck size={13} />
                      <span>Active Target</span>
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm font-medium text-cyan-400 mt-1">
                    {selectedPerson.profession || 'Independent Professional'}
                  </p>
                  {selectedPerson.biography && (
                    <p className="text-xs text-slate-400 mt-1.5 max-w-2xl leading-relaxed">
                      {selectedPerson.biography}
                    </p>
                  )}

                  {/* Profile Links */}
                  <div className="flex flex-wrap gap-2 mt-3">
                    {selectedPerson.social_profiles?.map((prof) => (
                      <a
                        key={prof.id}
                        href={prof.profile_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 transition-colors"
                      >
                        <Globe size={12} />
                        <span>{prof.platform}: @{prof.username || 'profile'}</span>
                        <ExternalLink size={10} />
                      </a>
                    ))}
                  </div>
                </div>

                {/* ACTION CONTROLS: Upload URL & Run Automated Discovery */}
                <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full md:w-auto">
                  <button
                    onClick={() => fetchPersonIntelligence(selectedPerson.id)}
                    className="btn btn-secondary p-2.5 shrink-0"
                    title="Refresh Data"
                  >
                    <RotateCw size={16} />
                  </button>

                  {/* Upload URL Button */}
                  <button
                    onClick={() => setShowUrlUploadModal(true)}
                    className="btn btn-secondary border-cyan-500/50 text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 text-xs sm:text-sm flex-1 sm:flex-none justify-center"
                  >
                    <Link2 size={15} />
                    <span>Upload / Analyze URL</span>
                  </button>

                  {/* Automated Discovery Run Button */}
                  <button
                    onClick={handleStartResearch}
                    disabled={isResearching}
                    className="btn btn-primary px-4 sm:px-5 py-2.5 text-xs sm:text-sm flex-1 sm:flex-none justify-center"
                  >
                    {isResearching ? (
                      <>
                        <RotateCw size={16} className="animate-spin" />
                        <span>Searching...</span>
                      </>
                    ) : (
                      <>
                        <Play size={16} fill="white" />
                        <span>Start Auto-Discovery</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* --- REAL-TIME RESEARCH PROGRESS BAR (IF RUNNING) --- */}
              {isResearching && (
                <div className="p-4 bg-cyan-950/20 border-b border-cyan-500/30">
                  <div className="flex justify-between items-center text-xs font-semibold mb-1.5">
                    <span className="text-cyan-400">
                      Discovery Pipeline in Progress: {jobStatus?.progress || 10}%
                    </span>
                    <span className="text-slate-400 font-mono uppercase">
                      Status: {jobStatus?.status || 'RUNNING'}
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-300 ease-out"
                      style={{ width: `${jobStatus?.progress || 15}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1.5">
                    Scraping YouTube, News Articles, Podcasts, and Event pages • Verifying identity and deduplicating...
                  </p>
                </div>
              )}

              {/* --- NAVIGATION TABS --- */}
              <div className="flex border-b border-slate-800 bg-slate-900/60 px-3 sm:px-6 overflow-x-auto scroll-smooth">
                {[
                  { id: 'overview', label: 'Executive Report', icon: FileText, count: null },
                  { id: 'appearances', label: 'Public Appearances', icon: Layers, count: appearances.length },
                  { id: 'timeline', label: 'Chronological Timeline', icon: Calendar, count: timeline.length },
                  { id: 'sources', label: 'Sources & Provenance', icon: Globe, count: sources.length },
                ].map((t) => {
                  const Icon = t.icon;
                  const isActive = activeTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id)}
                      className={`py-3 px-3 sm:px-4 text-xs font-semibold tracking-wide border-b-2 flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors ${
                        isActive
                          ? 'border-cyan-400 text-cyan-400'
                          : 'border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <Icon size={15} />
                      <span>{t.label}</span>
                      {t.count !== null && (
                        <span
                          className={`text-[11px] px-1.5 py-0.5 rounded-full ${
                            isActive
                              ? 'bg-cyan-500/20 text-cyan-400 font-bold'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {t.count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* --- TAB CONTENT AREA --- */}
              <div className="p-3.5 sm:p-6 flex-1">
                {loadingData && !isResearching ? (
                  <div className="text-center py-16 text-slate-500">
                    <RotateCw size={28} className="animate-spin mx-auto mb-3 opacity-50 text-cyan-400" />
                    <p className="text-sm">Loading intelligence data...</p>
                  </div>
                ) : (
                  <>
                    {/* --- TAB 1: EXECUTIVE OVERVIEW MODULE --- */}
                    {activeTab === 'overview' && (
                      <div className="flex flex-col gap-6">
                        <MetricsGrid reportData={reportData} appearances={appearances} sources={sources} />

                        {appearances.length === 0 ? (
                          /* FRIENDLY EMPTY STATE WHEN NO SEARCH HAS BEEN RUN YET */
                          <div className="glass-panel p-8 rounded-2xl border border-slate-800 bg-slate-900/50 text-center max-w-2xl mx-auto my-6">
                            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto mb-4 border border-cyan-500/20">
                              <Sparkles size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-100">
                              No appearances collected for {selectedPerson.name} yet
                            </h3>
                            <p className="text-xs text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
                              Choose how you would like to collect intelligence for this target:
                            </p>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 text-left">
                              <div
                                onClick={handleStartResearch}
                                className="p-4 rounded-xl border border-slate-800 bg-slate-900 hover:border-cyan-500/50 cursor-pointer transition-all group"
                              >
                                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs mb-1">
                                  <Play size={14} fill="currentColor" />
                                  <span>Automated Web Search</span>
                                </div>
                                <p className="text-xs text-slate-400 leading-normal">
                                  Automatically searches YouTube, Podcasts, News, and Events across the web.
                                </p>
                              </div>

                              <div
                                onClick={() => setShowUrlUploadModal(true)}
                                className="p-4 rounded-xl border border-slate-800 bg-slate-900 hover:border-cyan-500/50 cursor-pointer transition-all group"
                              >
                                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs mb-1">
                                  <Link2 size={14} />
                                  <span>Analyze a Specific Link</span>
                                </div>
                                <p className="text-xs text-slate-400 leading-normal">
                                  Paste any YouTube interview, podcast, or news article URL to analyze immediately.
                                </p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <>
                            {/* Executive Summary Card */}
                            <div className="glass-panel p-6 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
                              <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                                <Activity size={18} className="text-cyan-400" />
                                <span>Executive Summary</span>
                              </h3>
                              <p className="text-sm text-slate-300 leading-relaxed">
                                {reportData?.executive_summary ||
                                  `Identified ${appearances.length} public appearances across interviews, podcasts, and media for ${selectedPerson.name}.`}
                              </p>
                            </div>

                            {/* Topics and Statements 2-Column Grid */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                              <TopicCloud topics={reportData?.recurring_topics} />
                              <EvidenceQuotes statements={reportData?.important_statements} />
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {/* --- TAB 2: APPEARANCES MODULE --- */}
                    {activeTab === 'appearances' && (
                      <AppearanceList
                        appearances={appearances}
                        onDeleteAppearance={handleDeleteAppearance}
                      />
                    )}

                    {/* --- TAB 3: TIMELINE MODULE --- */}
                    {activeTab === 'timeline' && <TimelineView timeline={timeline} />}

                    {/* --- TAB 4: SOURCES & PROVENANCE MODULE --- */}
                    {activeTab === 'sources' && <SourcesTable sources={sources} />}
                  </>
                )}
              </div>
            </>
          ) : (
            /* ONBOARDING HERO WHEN ZERO PERSONS IN DATABASE */
            <div className="m-auto text-center p-8 max-w-xl">
              <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto mb-5 border border-cyan-500/20 shadow-[0_0_25px_rgba(6,182,212,0.15)]">
                <Radar size={32} />
              </div>
              <h2 className="text-2xl font-bold text-slate-100">
                Welcome to Person Intelligence
              </h2>
              <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                Discover, transcribe, and analyze public interviews, podcasts, news coverage, and conference talks for any individual.
              </p>

              {/* 3 Step Visual Guide */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-8 text-left">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center mb-2">
                    1
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">Add a Person</h4>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Enter the name & profession of the individual.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center mb-2">
                    2
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">Run Discovery</h4>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Auto-search public sources or paste any video/article link.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center mb-2">
                    3
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">Get AI Insights</h4>
                  <p className="text-[11px] text-slate-400 mt-1">
                    View verified appearances, video transcripts & timeline.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowRegisterModal(true)}
                className="btn btn-primary px-6 py-3 text-sm font-semibold shadow-lg shadow-cyan-500/20"
              >
                <PlusCircle size={18} />
                <span>Add Your First Person to Start</span>
              </button>
            </div>
          )}
        </main>
      </div>

      {/* --- REGISTER TARGET MODAL --- */}
      <RegisterTargetModal
        isOpen={showRegisterModal}
        onClose={() => setShowRegisterModal(false)}
        onTargetRegistered={(newPerson) => {
          setPersons((prev) => [newPerson, ...prev]);
          setSelectedPersonId(newPerson.id);
        }}
      />

      {/* --- DIRECT URL UPLOAD & ANALYZE MODAL --- */}
      <UrlUploadModal
        isOpen={showUrlUploadModal}
        onClose={() => setShowUrlUploadModal(false)}
        personId={selectedPerson?.id}
        personName={selectedPerson?.name}
        onAppearanceCreated={() => {
          if (selectedPerson?.id) {
            fetchPersonIntelligence(selectedPerson.id);
          }
        }}
      />
    </div>
  );
}
