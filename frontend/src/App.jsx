import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  Menu,
  UserCheck,
  AlertCircle,
  X
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
import TargetAccountPage from './modules/profile/TargetAccountPage';
import DownloadMenu from './modules/profile/DownloadMenu';
import { downloadPersonReport, downloadAllTargetsReport } from './utils/exportReport';

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [persons, setPersons] = useState([]);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const selectedPersonIdRef = useRef(null);
  useEffect(() => {
    selectedPersonIdRef.current = selectedPersonId;
  }, [selectedPersonId]);
  const selectedPerson = persons.find((p) => p.id === selectedPersonId) || null;

  // Per-target Active Research State: { [personId]: { jobId, status } }
  const [activeJobsByPerson, setActiveJobsByPerson] = useState({});
  const [jobErrorsByPerson, setJobErrorsByPerson] = useState({});
  const currentResearch = selectedPersonId ? activeJobsByPerson[selectedPersonId] || null : null;
  const selectedJobError = selectedPersonId ? jobErrorsByPerson[selectedPersonId] || null : null;
  const isSelectedResearching = Boolean(currentResearch);
  const selectedJobStatus = currentResearch?.status || null;
  const researchingPersonIds = Object.keys(activeJobsByPerson);

  // Active Tab
  const [activeTab, setActiveTab] = useState('account'); // account, overview, appearances, timeline, sources

  // Intelligence Data
  const [reportData, setReportData] = useState(null);
  const [appearances, setAppearances] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sources, setSources] = useState([]);
  const [insightsHistory, setInsightsHistory] = useState(null);
  const [loadingData, setLoadingData] = useState(false);

  // Modal States
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showUrlUploadModal, setShowUrlUploadModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const fetchPersonIntelligence = useCallback(async (personId) => {
    if (!personId) return;
    setLoadingData(true);
    try {
      const [personRes, rep, apps, tm, srcs, ins] = await Promise.allSettled([
        api.getPerson(personId),
        api.getReport(personId),
        api.getAppearances(personId),
        api.getTimeline(personId),
        api.getSources(personId),
        api.getInsights(personId),
      ]);

      if (personRes.status === 'fulfilled' && personRes.value) {
        const freshPerson = personRes.value;
        setPersons((prev) => prev.map((p) => (p.id === personId ? freshPerson : p)));
      }

      if (selectedPersonIdRef.current === personId) {
        setReportData(rep.status === 'fulfilled' ? rep.value : null);
        setAppearances(apps.status === 'fulfilled' ? apps.value : []);
        setTimeline(tm.status === 'fulfilled' ? tm.value : []);
        setSources(srcs.status === 'fulfilled' ? srcs.value : []);
        setInsightsHistory(ins.status === 'fulfilled' ? ins.value : null);
      }
    } catch (err) {
      console.error('Error loading person intelligence:', err);
    } finally {
      if (selectedPersonIdRef.current === personId) {
        setLoadingData(false);
      }
    }
  }, []);

  // 1. Initial Load & Backend Health Ping
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const isUp = await api.checkHealth();
        if (active) setBackendOnline(isUp);
        const list = await api.getPersons();
        if (!active) return;
        setPersons(list);
        if (list.length > 0) {
          setSelectedPersonId((curr) => curr || list[0].id);
        }
      } catch (err) {
        console.error('Initial load error:', err);
        if (active) setBackendOnline(false);
      }
    }
    load();

    const interval = setInterval(async () => {
      try {
        const isUp = await api.checkHealth();
        setBackendOnline(isUp);
      } catch {
        setBackendOnline(false);
      }
    }, 45000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  function handleSelectPerson(personId) {
    if (personId === selectedPersonId) return;
    setReportData(null);
    setAppearances([]);
    setTimeline([]);
    setSources([]);
    setInsightsHistory(null);
    setSelectedPersonId(personId);
  }

  // 2. Load Selected Target Data when target switches
  useEffect(() => {
    if (!selectedPersonId) return;
    fetchPersonIntelligence(selectedPersonId);
  }, [selectedPersonId, fetchPersonIntelligence]);

  // 3. Trigger Discovery Pipeline strictly for the requested target person
  async function handleStartResearch() {
    const targetPersonId = selectedPersonId;
    if (!targetPersonId || activeJobsByPerson[targetPersonId]) return;
    try {
      setJobErrorsByPerson((prev) => {
        if (!prev[targetPersonId]) return prev;
        const next = { ...prev };
        delete next[targetPersonId];
        return next;
      });
      setActiveJobsByPerson((prev) => ({
        ...prev,
        [targetPersonId]: { jobId: null, status: { status: 'STARTING', progress: 5 } },
      }));
      const res = await api.startResearch(targetPersonId);
      setActiveJobsByPerson((prev) => ({
        ...prev,
        [targetPersonId]: { jobId: res.id, status: res },
      }));
    } catch (err) {
      alert(`Failed to start research: ${err.message}`);
      setActiveJobsByPerson((prev) => {
        const next = { ...prev };
        delete next[targetPersonId];
        return next;
      });
    }
  }

  // 4. Poll Research Progress independently per active target
  useEffect(() => {
    const activeEntries = Object.entries(activeJobsByPerson).filter(([, info]) => info?.jobId);
    if (activeEntries.length === 0) return;

    const interval = setInterval(async () => {
      await Promise.all(
        activeEntries.map(async ([personId, info]) => {
          try {
            const status = await api.getResearchStatus(info.jobId);
            if (status.status === 'COMPLETED' || status.status === 'FAILED') {
              setActiveJobsByPerson((prev) => {
                const next = { ...prev };
                delete next[personId];
                return next;
              });
              if (status.status === 'FAILED') {
                setJobErrorsByPerson((prev) => ({
                  ...prev,
                  [personId]: status.error_message || 'Search pipeline failed before completing.',
                }));
              }
              if (selectedPersonIdRef.current === personId) {
                fetchPersonIntelligence(personId);
              }
            } else {
              setActiveJobsByPerson((prev) => {
                if (!prev[personId]) return prev;
                return {
                  ...prev,
                  [personId]: { ...prev[personId], status },
                };
              });
            }
          } catch (err) {
            console.error('Polling error:', err);
          }
        })
      );
    }, 2500);

    return () => clearInterval(interval);
  }, [activeJobsByPerson, fetchPersonIntelligence]);

  // 5. Delete Person
  async function handleDeletePerson(personId) {
    try {
      await api.deletePerson(personId);
      const remaining = persons.filter((p) => p.id !== personId);
      setPersons(remaining);
      if (selectedPersonId === personId) {
        setReportData(null);
        setAppearances([]);
        setTimeline([]);
        setSources([]);
        setInsightsHistory(null);
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

  // 7. Generate AI Insights
  async function handleGenerateInsights(personId, focusNotes = null) {
    const created = await api.generateInsights(personId, { focus_notes: focusNotes });
    const latestHistory = await api.getInsights(personId);
    setSelectedPersonId((currId) => {
      if (currId === personId) {
        setInsightsHistory(latestHistory);
      }
      return currId;
    });
    return created;
  }

  // 8. Export / Download Reports straight to browser Downloads folder
  async function handleDownloadAllTargets(format) {
    try {
      const targetList = persons.length > 0 ? persons : await api.getPersons();
      const bundles = await Promise.all(
        targetList.map(async (p) => {
          const [personRes, appsRes, srcsRes, insRes] = await Promise.allSettled([
            api.getPerson(p.id),
            api.getAppearances(p.id),
            api.getSources(p.id),
            api.getInsights(p.id),
          ]);
          return {
            person: personRes.status === 'fulfilled' ? personRes.value : p,
            appearances: appsRes.status === 'fulfilled' ? appsRes.value : [],
            sources: srcsRes.status === 'fulfilled' ? srcsRes.value : [],
            insightsReport: insRes.status === 'fulfilled' ? insRes.value?.latest_report || null : null,
          };
        })
      );
      downloadAllTargetsReport({ format, bundles });
    } catch (err) {
      alert(`Failed to export reports: ${err.message}`);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-white text-slate-900 font-sans">
      {/* --- SIMPLE CLEAN TOP NAVBAR --- */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-40 px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden p-2 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 shrink-0"
            title="Open People List"
            aria-label="Open People List"
          >
            <Menu size={20} />
          </button>

          <div className="p-2 rounded-xl bg-blue-600 shadow-sm shrink-0">
            <Radar size={20} className="text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-bold tracking-tight text-slate-900 truncate">
              Leadzen <span className="text-blue-600">Intelligence</span>
            </h1>
            <p className="text-xs text-slate-500 truncate hidden sm:block">
              Simple People Research, Public Appearances & AI Insights
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold border ${
              backendOnline
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-rose-50 border-rose-200 text-rose-700'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            />
            <span className="hidden sm:inline">
              {backendOnline ? 'System Ready' : 'Connecting...'}
            </span>
            <span className="sm:hidden">{backendOnline ? 'Ready' : 'Offline'}</span>
          </div>

          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="text-xs font-medium text-slate-500 hover:text-blue-600 transition-colors inline-flex items-center gap-1"
          >
            <span className="hidden sm:inline">API Docs</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </header>

      {/* --- MAIN LAYOUT --- */}
      <div className="flex flex-1 overflow-hidden relative bg-white">
        {/* Sidebar: People Selector */}
        <TargetSelector
          persons={persons}
          selectedPersonId={selectedPersonId}
          researchingPersonIds={researchingPersonIds}
          onSelectPerson={handleSelectPerson}
          onOpenRegisterModal={() => setShowRegisterModal(true)}
          onDeletePerson={handleDeletePerson}
          mobileOpen={mobileMenuOpen}
          onCloseMobile={() => setMobileMenuOpen(false)}
        />

        {/* Workspace Panel */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-white">
          {selectedPerson ? (
            <>
              {/* Target Summary & Quick Controls */}
              <div className="p-4 sm:p-6 border-b border-slate-200 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h2
                      onClick={() => setActiveTab('account')}
                      className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 hover:text-blue-600 cursor-pointer transition-colors"
                    >
                      {selectedPerson.name}
                    </h2>
                    <span className="badge badge-verified">
                      <ShieldCheck size={13} />
                      <span>Active</span>
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm font-medium text-blue-700 mt-1">
                    {selectedPerson.profession || 'Independent Professional'}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2.5">
                    {selectedPerson.social_profiles?.map((prof) => (
                      <a
                        key={prof.id}
                        href={prof.profile_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-blue-700 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 transition-colors"
                      >
                        <Globe size={12} />
                        <span>{prof.platform}: @{prof.username || 'profile'}</span>
                        <ExternalLink size={10} />
                      </a>
                    ))}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center gap-2.5">
                  <button
                    onClick={() => fetchPersonIntelligence(selectedPerson.id)}
                    className="btn btn-secondary p-2.5 shrink-0"
                    title="Refresh Data"
                  >
                    <RotateCw size={16} />
                  </button>

                  <button
                    onClick={() => setShowUrlUploadModal(true)}
                    className="btn btn-secondary text-xs sm:text-sm"
                  >
                    <Link2 size={15} />
                    <span>Add Link</span>
                  </button>

                  <DownloadMenu
                    personName={selectedPerson.name}
                    personsCount={persons.length}
                    onDownloadPerson={(format) =>
                      downloadPersonReport({
                        format,
                        person: selectedPerson,
                        appearances,
                        sources,
                        insightsReport: insightsHistory?.latest_report || null,
                      })
                    }
                    onDownloadAll={handleDownloadAllTargets}
                  />

                  <button
                    onClick={handleStartResearch}
                    disabled={isSelectedResearching}
                    className="btn btn-primary px-4 py-2 text-xs sm:text-sm"
                  >
                    {isSelectedResearching ? (
                      <>
                        <RotateCw size={15} className="animate-spin" />
                        <span>Searching...</span>
                      </>
                    ) : (
                      <>
                        <Play size={15} fill="white" />
                        <span>Search Web & Social</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Research Progress Strip (Shown ONLY for the actively researching person) */}
              {isSelectedResearching && (
                <div className="p-4 bg-blue-50 border-b border-blue-200">
                  <div className="flex justify-between items-center text-xs font-semibold mb-1.5">
                    <span className="text-blue-800">
                      Searching web, YouTube, podcasts & social links for {selectedPerson.name}: {selectedJobStatus?.progress || 10}%
                    </span>
                    <span className="text-blue-700 font-mono uppercase">
                      {selectedJobStatus?.status || 'RUNNING'}
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-blue-100 overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all duration-300 ease-out"
                      style={{ width: `${selectedJobStatus?.progress || 15}%` }}
                    />
                  </div>
                </div>
              )}

              {selectedJobError && !isSelectedResearching && (
                <div className="px-4 sm:px-6 py-3 bg-rose-50 border-b border-rose-200 flex items-center justify-between gap-3 text-xs text-rose-800">
                  <div className="flex items-center gap-2">
                    <AlertCircle size={15} className="shrink-0 text-rose-600" />
                    <span>Search job failed: {selectedJobError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setJobErrorsByPerson((prev) => {
                        const next = { ...prev };
                        delete next[selectedPerson.id];
                        return next;
                      })
                    }
                    className="p-1 rounded text-rose-500 hover:text-rose-800 hover:bg-rose-100"
                    aria-label="Dismiss search error"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}

              {/* Simple Navigation Tabs */}
              <div className="flex border-b border-slate-200 bg-slate-50/60 px-3 sm:px-6 overflow-x-auto">
                {[
                  { id: 'account', label: 'Account & AI Insights', icon: UserCheck, count: null },
                  { id: 'overview', label: 'Summary Report', icon: FileText, count: null },
                  { id: 'appearances', label: 'Appearances', icon: Layers, count: appearances.length },
                  { id: 'timeline', label: 'Timeline', icon: Calendar, count: timeline.length },
                  { id: 'sources', label: 'All Sources', icon: Globe, count: sources.length },
                ].map((t) => {
                  const Icon = t.icon;
                  const isActive = activeTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id)}
                      className={`py-3 px-3 sm:px-4 text-xs font-semibold border-b-2 flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors ${
                        isActive
                          ? 'border-blue-600 text-blue-700 bg-white'
                          : 'border-transparent text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Icon size={15} />
                      <span>{t.label}</span>
                      {t.count !== null && (
                        <span
                          className={`text-[11px] px-1.5 py-0.5 rounded-full ${
                            isActive
                              ? 'bg-blue-100 text-blue-700 font-bold'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {t.count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Workspace Body */}
              <div className="p-4 sm:p-6 flex-1 bg-white">
                {loadingData && !isSelectedResearching ? (
                  <div className="text-center py-16 text-slate-500">
                    <RotateCw size={28} className="animate-spin mx-auto mb-3 text-blue-600" />
                    <p className="text-sm">Loading profile data...</p>
                  </div>
                ) : (
                  <>
                    {activeTab === 'account' && (
                      <TargetAccountPage
                        key={selectedPerson.id}
                        person={selectedPerson}
                        appearances={appearances}
                        sources={sources}
                        insightsHistory={insightsHistory}
                        onStartResearch={handleStartResearch}
                        isResearching={isSelectedResearching}
                        onOpenUrlModal={() => setShowUrlUploadModal(true)}
                        onDeleteAppearance={handleDeleteAppearance}
                        onEnrichLinkedIn={async (personId, force = false) => {
                          const res = await api.enrichLinkedInProfile(personId, { force });
                          const refreshed = await api.getPerson(personId);
                          setPersons((prev) => prev.map((p) => (p.id === personId ? refreshed : p)));
                          return res;
                        }}
                        onGenerateInsights={handleGenerateInsights}
                      />
                    )}

                    {activeTab === 'overview' && (
                      <div className="flex flex-col gap-6 max-w-7xl mx-auto">
                        <MetricsGrid reportData={reportData} appearances={appearances} sources={sources} />

                        {appearances.length === 0 ? (
                          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center max-w-2xl mx-auto my-6 shadow-sm">
                            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4 border border-blue-200">
                              <Sparkles size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900">
                              No public appearances found for {selectedPerson.name} yet
                            </h3>
                            <p className="text-sm text-slate-600 mt-2 max-w-md mx-auto">
                              Start an automated web search or paste any YouTube/article URL to analyze:
                            </p>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 text-left">
                              <div
                                onClick={handleStartResearch}
                                className="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:border-blue-400 cursor-pointer transition-all"
                              >
                                <div className="flex items-center gap-2 text-blue-700 font-semibold text-xs mb-1">
                                  <Play size={14} fill="currentColor" />
                                  <span>Search Web & Social</span>
                                </div>
                                <p className="text-xs text-slate-600">
                                  Automatically finds LinkedIn, YouTube, podcasts, and news articles.
                                </p>
                              </div>

                              <div
                                onClick={() => setShowUrlUploadModal(true)}
                                className="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:border-blue-400 cursor-pointer transition-all"
                              >
                                <div className="flex items-center gap-2 text-blue-700 font-semibold text-xs mb-1">
                                  <Link2 size={14} />
                                  <span>Analyze a Link</span>
                                </div>
                                <p className="text-xs text-slate-600">
                                  Paste any specific video, podcast, or article link to extract immediately.
                                </p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                              <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                                <Activity size={18} className="text-blue-600" />
                                <span>Executive Summary</span>
                              </h3>
                              <p className="text-sm text-slate-700 leading-relaxed">
                                {reportData?.executive_summary ||
                                  `Identified ${appearances.length} public appearances across interviews, podcasts, and media for ${selectedPerson.name}.`}
                              </p>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                              <TopicCloud topics={reportData?.recurring_topics} />
                              <EvidenceQuotes statements={reportData?.important_statements} />
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {activeTab === 'appearances' && (
                      <div className="max-w-7xl mx-auto">
                        <AppearanceList
                          appearances={appearances}
                          onDeleteAppearance={handleDeleteAppearance}
                        />
                      </div>
                    )}

                    {activeTab === 'timeline' && <TimelineView timeline={timeline} />}

                    {activeTab === 'sources' && (
                      <div className="max-w-7xl mx-auto">
                        <SourcesTable sources={sources} />
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="m-auto text-center p-8 max-w-xl">
              <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-5 border border-blue-200">
                <Radar size={32} />
              </div>
              <h2 className="text-2xl font-bold text-slate-900">
                Welcome to Leadzen Intelligence
              </h2>
              <p className="text-sm text-slate-600 mt-2 leading-relaxed">
                Add any executive, founder, or prospect to collect public appearances, enrich LinkedIn backgrounds, and generate structured AI insights.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-8 text-left">
                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
                  <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-700 text-xs font-bold flex items-center justify-center mb-2">
                    1
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Add a Person</h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Enter their name and company or role.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
                  <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-700 text-xs font-bold flex items-center justify-center mb-2">
                    2
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Collect Information</h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Search YouTube, LinkedIn, podcasts, and news.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
                  <div className="w-6 h-6 rounded-full bg-blue-50 text-blue-700 text-xs font-bold flex items-center justify-center mb-2">
                    3
                  </div>
                  <h4 className="text-xs font-bold text-slate-900">Generate AI Insights</h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Get structured 7-section executive briefings.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowRegisterModal(true)}
                className="btn btn-primary px-6 py-3 text-sm font-semibold"
              >
                <PlusCircle size={18} />
                <span>Add Your First Person</span>
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Register Modal */}
      <RegisterTargetModal
        isOpen={showRegisterModal}
        onClose={() => setShowRegisterModal(false)}
        onTargetRegistered={(newPerson) => {
          setPersons((prev) => [newPerson, ...prev]);
          setAppearances([]);
          setReportData(null);
          setTimeline([]);
          setSources([]);
          setInsightsHistory(null);
          setSelectedPersonId(newPerson.id);
          setActiveTab('account');
        }}
      />

      {/* Analyze Specific URL Modal */}
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
