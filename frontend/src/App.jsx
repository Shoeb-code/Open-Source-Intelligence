import React, { useState, useEffect } from 'react';
import {
  Radar,
  UserPlus,
  Play,
  RotateCw,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  FileText,
  Video,
  Newspaper,
  Mic,
  Calendar,
  Layers,
  Search,
  Quote,
  TrendingUp,
  User,
  Activity,
  Globe
} from 'lucide-react';
import { api } from './api';

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [persons, setPersons] = useState([]);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);

  // Active Research State
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [isResearching, setIsResearching] = useState(false);

  // Tab State
  const [activeTab, setActiveTab] = useState('overview'); // overview, appearances, timeline, sources
  const [appearanceFilter, setAppearanceFilter] = useState('ALL');

  // Loaded Data
  const [reportData, setReportData] = useState(null);
  const [appearances, setAppearances] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sources, setSources] = useState([]);
  const [loadingData, setLoadingData] = useState(false);

  // Registration Modal State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [formName, setFormName] = useState('');
  const [formProfession, setFormProfession] = useState('');
  const [formBio, setFormBio] = useState('');
  const [formLinkedin, setFormLinkedin] = useState('');
  const [formYoutube, setFormYoutube] = useState('');
  const [formInstagram, setFormInstagram] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // 1. Initial Load & Backend Health
  useEffect(() => {
    checkHealthAndLoad();
    const interval = setInterval(checkHealthAndLoad, 15000);
    return () => clearInterval(interval);
  }, []);

  async function checkHealthAndLoad() {
    const isUp = await api.checkHealth();
    setBackendOnline(isUp);
    if (isUp) {
      loadPersons();
    }
  }

  async function loadPersons() {
    try {
      const list = await api.getPersons();
      setPersons(list);
      if (list.length > 0 && !selectedPersonId) {
        setSelectedPersonId(list[0].id);
      }
    } catch (err) {
      console.error('Error loading persons:', err);
    }
  }

  // 2. Fetch Selected Person Details & Data
  useEffect(() => {
    if (!selectedPersonId) return;
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

  // 3. Trigger Research Pipeline
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

  // 5. Register Person Handler
  async function handleRegisterPerson(e) {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    try {
      const newPerson = await api.createPerson({
        name: formName,
        profession: formProfession || null,
        biography: formBio || null,
        linkedin_url: formLinkedin || null,
        youtube_url: formYoutube || null,
        instagram_url: formInstagram || null,
      });

      setPersons((prev) => [newPerson, ...prev]);
      setSelectedPersonId(newPerson.id);
      setShowRegisterModal(false);

      // Reset Form
      setFormName('');
      setFormProfession('');
      setFormBio('');
      setFormLinkedin('');
      setFormYoutube('');
      setFormInstagram('');
    } catch (err) {
      setFormError(err.message);
    } finally {
      setFormSubmitting(false);
    }
  }

  // Filtered Appearances
  const filteredAppearances = appearances.filter((item) => {
    if (appearanceFilter === 'ALL') return true;
    return item.identity_status === appearanceFilter;
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* --- TOP NAVBAR --- */}
      <header
        style={{
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(17, 24, 39, 0.95)',
          backdropFilter: 'blur(10px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          padding: '0.85rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
              padding: '0.5rem',
              borderRadius: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)',
            }}
          >
            <Radar size={22} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              PUBLIC APPEARANCE <span style={{ color: 'var(--accent-cyan)' }}>INTELLIGENCE</span>
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Level 2 • Public Source Discovery, Content Extraction & AI Analysis
            </p>
          </div>
        </div>

        {/* Backend Status Pill & Links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.3rem 0.75rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 500,
              background: backendOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
              border: backendOnline
                ? '1px solid rgba(16, 185, 129, 0.3)'
                : '1px solid rgba(244, 63, 94, 0.3)',
              color: backendOnline ? '#34d399' : '#fb7185',
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: backendOnline ? '#10b981' : '#f43f5e',
                boxShadow: backendOnline ? '0 0 8px #10b981' : 'none',
              }}
            />
            {backendOnline ? 'Backend Online (Port 8000)' : 'Connecting to Backend...'}
          </div>

          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            style={{
              color: 'var(--text-muted)',
              fontSize: '0.8rem',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            API Swagger Docs <ExternalLink size={13} />
          </a>
        </div>
      </header>

      {/* --- MAIN LAYOUT --- */}
      <div style={{ display: 'flex', flex: 1 }}>
        {/* --- LEFT SIDEBAR: TARGET PROFILES --- */}
        <aside
          style={{
            width: '320px',
            borderRight: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              padding: '1.25rem',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <User size={18} color="var(--accent-cyan)" />
              <h2 style={{ fontSize: '0.9rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Target Profiles
              </h2>
            </div>
            <button
              onClick={() => setShowRegisterModal(true)}
              className="btn btn-primary"
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
            >
              <UserPlus size={14} /> New
            </button>
          </div>

          {/* List of Persons */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
            {persons.length === 0 ? (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-dim)' }}>
                <User size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.85rem' }}>No targets registered yet.</p>
                <button
                  onClick={() => setShowRegisterModal(true)}
                  className="btn btn-secondary"
                  style={{ marginTop: '0.75rem', fontSize: '0.75rem', width: '100%' }}
                >
                  Register First Person
                </button>
              </div>
            ) : (
              persons.map((p) => {
                const isSelected = p.id === selectedPersonId;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPersonId(p.id)}
                    style={{
                      padding: '0.85rem',
                      borderRadius: '0.5rem',
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid transparent',
                      background: isSelected ? 'var(--bg-card)' : 'transparent',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: isSelected ? '#38bdf8' : 'var(--text-main)' }}>
                        {p.name}
                      </h3>
                      {isSelected && (
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-cyan)' }} />
                      )}
                    </div>
                    <p
                      style={{
                        fontSize: '0.775rem',
                        color: 'var(--text-muted)',
                        marginTop: '0.2rem',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {p.profession || 'Independent Professional'}
                    </p>
                    <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.5rem' }}>
                      {p.social_profiles?.map((sp) => (
                        <span
                          key={sp.id}
                          style={{
                            fontSize: '0.65rem',
                            padding: '0.15rem 0.4rem',
                            borderRadius: '4px',
                            background: 'var(--border-subtle)',
                            color: 'var(--text-dim)',
                            textTransform: 'uppercase',
                          }}
                        >
                          {sp.platform}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* --- MAIN INTELLIGENCE DASHBOARD --- */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
          {selectedPerson ? (
            <>
              {/* --- TARGET HEADER & CONTROL BAR --- */}
              <div
                style={{
                  padding: '1.5rem',
                  borderBottom: '1px solid var(--border-color)',
                  background: 'var(--bg-card)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1.5rem',
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>{selectedPerson.name}</h2>
                    <span className="badge badge-verified">
                      <ShieldCheck size={13} /> Active Identity
                    </span>
                  </div>
                  <p style={{ color: 'var(--accent-cyan)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
                    {selectedPerson.profession || 'No title specified'}
                  </p>
                  {selectedPerson.biography && (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginTop: '0.4rem', maxWidth: '650px' }}>
                      {selectedPerson.biography}
                    </p>
                  )}

                  {/* Profile Links */}
                  <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.75rem' }}>
                    {selectedPerson.social_profiles?.map((prof) => (
                      <a
                        key={prof.id}
                        href={prof.profile_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                          fontSize: '0.75rem',
                          color: 'var(--text-muted)',
                          textDecoration: 'none',
                          padding: '0.25rem 0.6rem',
                          background: 'var(--bg-secondary)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '4px',
                        }}
                      >
                        <Globe size={12} /> {prof.platform}: @{prof.username || 'profile'} <ExternalLink size={10} />
                      </a>
                    ))}
                  </div>
                </div>

                {/* Research Trigger Button & Refresh */}
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <button
                    onClick={() => fetchPersonIntelligence(selectedPerson.id)}
                    className="btn btn-secondary"
                    title="Refresh Data"
                  >
                    <RotateCw size={15} />
                  </button>
                  <button
                    onClick={handleStartResearch}
                    disabled={isResearching}
                    className="btn btn-primary"
                    style={{ padding: '0.75rem 1.4rem', fontSize: '0.9rem' }}
                  >
                    {isResearching ? (
                      <>
                        <RotateCw size={16} className="animate-spin" /> Running Pipeline...
                      </>
                    ) : (
                      <>
                        <Play size={16} fill="white" /> Run Public Source Discovery
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* --- REAL-TIME RESEARCH PROGRESS BAR (IF RUNNING) --- */}
              {isResearching && (
                <div
                  style={{
                    padding: '1rem 1.5rem',
                    background: 'rgba(6, 182, 212, 0.08)',
                    borderBottom: '1px solid rgba(6, 182, 212, 0.3)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                      Research Execution in Progress: Stage {jobStatus?.progress || 10}%
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Status: {jobStatus?.status || 'RUNNING'}
                    </span>
                  </div>
                  <div
                    style={{
                      width: '100%',
                      height: '8px',
                      background: 'var(--bg-secondary)',
                      borderRadius: '999px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${jobStatus?.progress || 15}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #06b6d4, #3b82f6)',
                        transition: 'width 0.4s ease',
                      }}
                    />
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.4rem' }}>
                    Scraping YouTube, News Articles, Podcasts, and Conference talks • Verifying identity and deduplicating...
                  </p>
                </div>
              )}

              {/* --- NAVIGATION TABS --- */}
              <div
                style={{
                  display: 'flex',
                  borderBottom: '1px solid var(--border-color)',
                  background: 'var(--bg-secondary)',
                  padding: '0 1.5rem',
                }}
              >
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
                      style={{
                        padding: '1rem 1.25rem',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)',
                        background: 'transparent',
                        border: 'none',
                        borderBottom: isActive ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.45rem',
                      }}
                    >
                      <Icon size={16} />
                      {t.label}
                      {t.count !== null && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            background: isActive ? 'rgba(6, 182, 212, 0.2)' : 'var(--bg-card)',
                            color: isActive ? 'var(--accent-cyan)' : 'var(--text-dim)',
                            padding: '0.1rem 0.45rem',
                            borderRadius: '999px',
                          }}
                        >
                          {t.count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* --- TAB CONTENT AREA --- */}
              <div style={{ padding: '1.5rem', flex: 1 }}>
                {loadingData && !isResearching ? (
                  <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
                    <RotateCw size={28} className="animate-spin" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                    <p>Loading intelligence data...</p>
                  </div>
                ) : (
                  <>
                    {/* --- TAB 1: EXECUTIVE OVERVIEW --- */}
                    {activeTab === 'overview' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {/* Statistics Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem' }}>
                          <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-dim)' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                                Total Discovered
                              </span>
                              <Search size={18} />
                            </div>
                            <h3 style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.4rem', color: 'var(--text-main)' }}>
                              {reportData?.statistics?.total_appearances_discovered || appearances.length}
                            </h3>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                              Across public sources & web
                            </p>
                          </div>

                          <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-dim)' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                                Verified Matches
                              </span>
                              <ShieldCheck size={18} color="#34d399" />
                            </div>
                            <h3 style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.4rem', color: '#34d399' }}>
                              {reportData?.statistics?.verified_appearances ||
                                appearances.filter((a) => a.identity_status === 'VERIFIED').length}
                            </h3>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                              Multi-signal score &gt; 80%
                            </p>
                          </div>

                          <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-dim)' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                                Distinct Media Sources
                              </span>
                              <Globe size={18} color="var(--accent-blue)" />
                            </div>
                            <h3 style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.4rem', color: '#60a5fa' }}>
                              {reportData?.statistics?.total_distinct_sources || sources.length}
                            </h3>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                              Unique URLs and domains
                            </p>
                          </div>

                          <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-dim)' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                                Top Format
                              </span>
                              <Video size={18} color="#f472b6" />
                            </div>
                            <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '0.4rem', color: '#f472b6' }}>
                              {appearances[0]?.appearance_type || 'Interviews'}
                            </h3>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                              Dominant medium
                            </p>
                          </div>
                        </div>

                        {/* Executive Summary Card */}
                        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '0.75rem' }}>
                          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Activity size={18} color="var(--accent-cyan)" /> Executive Summary
                          </h3>
                          <p style={{ color: 'var(--text-main)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                            {reportData?.executive_summary ||
                              (appearances.length > 0
                                ? `Identified ${appearances.length} public appearances across interviews, podcasts, and media for ${selectedPerson.name}. Verification scores indicate high relevance.`
                                : `No public appearances recorded yet. Click "Run Public Source Discovery" above to initiate search and analysis.`)}
                          </p>
                        </div>

                        {/* Topics and Statements 2-Column Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
                          {/* Recurring Topics */}
                          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '0.75rem' }}>
                            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                              <TrendingUp size={16} color="var(--accent-cyan)" /> Recurring Topics & Themes
                            </h4>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                              {reportData?.recurring_topics && reportData.recurring_topics.length > 0 ? (
                                reportData.recurring_topics.map((t, idx) => (
                                  <span
                                    key={idx}
                                    style={{
                                      background: 'var(--bg-secondary)',
                                      border: '1px solid var(--border-color)',
                                      padding: '0.35rem 0.75rem',
                                      borderRadius: '999px',
                                      fontSize: '0.8rem',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '0.4rem',
                                    }}
                                  >
                                    <span>{t.topic}</span>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                                      {t.count}
                                    </span>
                                  </span>
                                ))
                              ) : (
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                                  Topics will appear here after discovery.
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Top Statements & Evidence */}
                          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '0.75rem' }}>
                            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                              <Quote size={16} color="#fbbf24" /> Extracted Statements & Quotes
                            </h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                              {reportData?.important_statements && reportData.important_statements.length > 0 ? (
                                reportData.important_statements.slice(0, 4).map((stmt, idx) => (
                                  <div
                                    key={idx}
                                    style={{
                                      padding: '0.75rem',
                                      background: 'var(--bg-secondary)',
                                      borderRadius: '0.5rem',
                                      borderLeft: '3px solid #fbbf24',
                                    }}
                                  >
                                    <p style={{ fontSize: '0.85rem', fontStyle: 'italic', color: 'var(--text-main)' }}>
                                      "{stmt.statement}"
                                    </p>
                                    <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                                      Source: {stmt.source_title || 'Media Appearance'}
                                    </p>
                                  </div>
                                ))
                              ) : (
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                                  Direct evidence quotes will appear here after analysis.
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* --- TAB 2: PUBLIC APPEARANCES --- */}
                    {activeTab === 'appearances' && (
                      <div>
                        {/* Filter Bar */}
                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
                          {['ALL', 'VERIFIED', 'LIKELY_MATCH', 'NEEDS_REVIEW'].map((f) => (
                            <button
                              key={f}
                              onClick={() => setAppearanceFilter(f)}
                              style={{
                                padding: '0.4rem 0.85rem',
                                borderRadius: '999px',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                border: '1px solid',
                                borderColor: appearanceFilter === f ? 'var(--accent-cyan)' : 'var(--border-color)',
                                background: appearanceFilter === f ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                                color: appearanceFilter === f ? 'var(--accent-cyan)' : 'var(--text-muted)',
                                cursor: 'pointer',
                              }}
                            >
                              {f.replace('_', ' ')}
                            </button>
                          ))}
                        </div>

                        {/* Appearances List */}
                        {filteredAppearances.length === 0 ? (
                          <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', borderRadius: '0.75rem' }}>
                            <Layers size={36} style={{ margin: '0 auto 1rem', opacity: 0.3 }} />
                            <p style={{ color: 'var(--text-muted)' }}>No appearances match the selected filter.</p>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {filteredAppearances.map((item) => (
                              <div
                                key={item.id}
                                className="glass-panel"
                                style={{
                                  padding: '1.25rem',
                                  borderRadius: '0.75rem',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '0.75rem',
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                                  <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                                      <span
                                        className={`badge ${
                                          item.appearance_type === 'PODCAST'
                                            ? 'badge-podcast'
                                            : item.appearance_type === 'INTERVIEW'
                                            ? 'badge-interview'
                                            : item.appearance_type === 'CONFERENCE'
                                            ? 'badge-conference'
                                            : 'badge-news'
                                        }`}
                                      >
                                        {item.appearance_type}
                                      </span>
                                      <span
                                        className={`badge ${
                                          item.identity_status === 'VERIFIED'
                                            ? 'badge-verified'
                                            : item.identity_status === 'LIKELY_MATCH'
                                            ? 'badge-likely'
                                            : 'badge-review'
                                        }`}
                                      >
                                        {item.identity_status}
                                      </span>
                                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                                        Confidence: {Math.round(item.confidence_score * 100)}%
                                      </span>
                                    </div>
                                    <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
                                      {item.title}
                                    </h4>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                                      Publisher: {item.publisher || 'Web / Media'} •{' '}
                                      {item.published_at ? new Date(item.published_at).toLocaleDateString() : 'Recent'}
                                    </p>
                                  </div>

                                  {item.sources?.[0] && (
                                    <a
                                      href={item.sources[0].source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="btn btn-secondary"
                                      style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                                    >
                                      View Source <ExternalLink size={12} />
                                    </a>
                                  )}
                                </div>

                                {/* Summary */}
                                {item.analysis?.summary && (
                                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                                    {item.analysis.summary}
                                  </p>
                                )}

                                {/* Role and Key Points */}
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                                  {item.analysis?.person_role && (
                                    <span
                                      style={{
                                        fontSize: '0.7rem',
                                        background: 'var(--bg-secondary)',
                                        border: '1px solid var(--border-color)',
                                        padding: '0.2rem 0.5rem',
                                        borderRadius: '4px',
                                        color: 'var(--accent-cyan)',
                                        fontWeight: 600,
                                      }}
                                    >
                                      Role: {item.analysis.person_role}
                                    </span>
                                  )}
                                  {item.analysis?.topics?.map((topic, i) => (
                                    <span
                                      key={i}
                                      style={{
                                        fontSize: '0.7rem',
                                        background: 'var(--border-subtle)',
                                        padding: '0.2rem 0.5rem',
                                        borderRadius: '4px',
                                        color: 'var(--text-dim)',
                                      }}
                                    >
                                      #{topic}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* --- TAB 3: CHRONOLOGICAL TIMELINE --- */}
                    {activeTab === 'timeline' && (
                      <div style={{ maxWidth: '850px', margin: '0 auto', padding: '1rem 0' }}>
                        {timeline.length === 0 ? (
                          <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', borderRadius: '0.75rem' }}>
                            <Calendar size={36} style={{ margin: '0 auto 1rem', opacity: 0.3 }} />
                            <p style={{ color: 'var(--text-muted)' }}>No timeline entries available.</p>
                          </div>
                        ) : (
                          <div style={{ position: 'relative', borderLeft: '2px solid var(--border-color)', marginLeft: '1rem' }}>
                            {timeline.map((entry, idx) => (
                              <div key={idx} style={{ position: 'relative', paddingLeft: '2rem', paddingBottom: '2rem' }}>
                                {/* Timeline Dot */}
                                <div
                                  style={{
                                    position: 'absolute',
                                    left: '-9px',
                                    top: '0',
                                    width: '16px',
                                    height: '16px',
                                    borderRadius: '50%',
                                    background: 'var(--accent-cyan)',
                                    boxShadow: '0 0 10px var(--accent-cyan)',
                                    border: '3px solid var(--bg-primary)',
                                  }}
                                />

                                <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '0.75rem' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                                      {new Date(entry.date).toLocaleDateString(undefined, {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric',
                                      })}
                                    </span>
                                    <span className="badge badge-interview">{entry.appearance_type}</span>
                                  </div>
                                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                                    {entry.title}
                                  </h4>
                                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                                    Publisher: {entry.publisher || 'External Media'}
                                  </p>
                                  {entry.summary && (
                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.6rem', lineHeight: 1.5 }}>
                                      {entry.summary}
                                    </p>
                                  )}
                                  {entry.primary_source_url && (
                                    <a
                                      href={entry.primary_source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '0.3rem',
                                        fontSize: '0.75rem',
                                        color: 'var(--accent-cyan)',
                                        textDecoration: 'none',
                                        marginTop: '0.75rem',
                                      }}
                                    >
                                      Inspect Source <ExternalLink size={12} />
                                    </a>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* --- TAB 4: SOURCES & PROVENANCE --- */}
                    {activeTab === 'sources' && (
                      <div className="glass-panel" style={{ borderRadius: '0.75rem', overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                          <thead>
                            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                              <th style={{ padding: '0.85rem 1.25rem' }}>Source Type</th>
                              <th style={{ padding: '0.85rem 1.25rem' }}>URL Reference</th>
                              <th style={{ padding: '0.85rem 1.25rem' }}>Extraction Status</th>
                              <th style={{ padding: '0.85rem 1.25rem' }}>Collected At</th>
                            </tr>
                          </thead>
                          <tbody>
                            {sources.length === 0 ? (
                              <tr>
                                <td colSpan={4} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)' }}>
                                  No source provenance entries found.
                                </td>
                              </tr>
                            ) : (
                              sources.map((s) => (
                                <tr key={s.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                                  <td style={{ padding: '0.85rem 1.25rem' }}>
                                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{s.source_type}</span>
                                  </td>
                                  <td style={{ padding: '0.85rem 1.25rem', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    <a
                                      href={s.source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      style={{ color: '#38bdf8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                                    >
                                      {s.source_url} <ExternalLink size={12} />
                                    </a>
                                  </td>
                                  <td style={{ padding: '0.85rem 1.25rem' }}>
                                    <span
                                      className={`badge ${
                                        s.extraction_status === 'SUCCESS' ? 'badge-verified' : 'badge-review'
                                      }`}
                                    >
                                      {s.extraction_status}
                                    </span>
                                  </td>
                                  <td style={{ padding: '0.85rem 1.25rem', color: 'var(--text-dim)' }}>
                                    {new Date(s.collected_at).toLocaleString()}
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          ) : (
            <div style={{ margin: 'auto', textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <Radar size={48} color="var(--accent-cyan)" style={{ margin: '0 auto 1.5rem', opacity: 0.5 }} />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)' }}>
                No Target Selected
              </h3>
              <p style={{ marginTop: '0.4rem', maxWidth: '400px' }}>
                Select an existing person from the left sidebar or register a new target to start public appearance intelligence discovery.
              </p>
              <button
                onClick={() => setShowRegisterModal(true)}
                className="btn btn-primary"
                style={{ marginTop: '1.25rem' }}
              >
                <UserPlus size={16} /> Register New Person
              </button>
            </div>
          )}
        </main>
      </div>

      {/* --- REGISTRATION MODAL --- */}
      {showRegisterModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem',
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '520px',
              borderRadius: '0.75rem',
              padding: '1.75rem',
              background: 'var(--bg-card)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Register Target for Intelligence</h3>
              <button
                onClick={() => setShowRegisterModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            {formError && (
              <div
                style={{
                  padding: '0.75rem',
                  borderRadius: '0.5rem',
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: '#fb7185',
                  fontSize: '0.8rem',
                  marginBottom: '1rem',
                }}
              >
                {formError}
              </div>
            )}

            <form onSubmit={handleRegisterPerson} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  FULL NAME *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sundar Pichai"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="input-field"
                  style={{ marginTop: '0.3rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  PROFESSION & AFFILIATION
                </label>
                <input
                  type="text"
                  placeholder="e.g. CEO at Alphabet and Google"
                  value={formProfession}
                  onChange={(e) => setFormProfession(e.target.value)}
                  className="input-field"
                  style={{ marginTop: '0.3rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  BIOGRAPHY / CONTEXT
                </label>
                <textarea
                  rows={2}
                  placeholder="Short professional summary or background..."
                  value={formBio}
                  onChange={(e) => setFormBio(e.target.value)}
                  className="input-field"
                  style={{ marginTop: '0.3rem', resize: 'vertical' }}
                />
              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.85rem' }}>
                <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
                  KNOWN SOCIAL & CHANNEL PROFILES (OPTIONAL)
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <input
                    type="url"
                    placeholder="LinkedIn Profile URL"
                    value={formLinkedin}
                    onChange={(e) => setFormLinkedin(e.target.value)}
                    className="input-field"
                  />
                  <input
                    type="url"
                    placeholder="YouTube Channel URL"
                    value={formYoutube}
                    onChange={(e) => setFormYoutube(e.target.value)}
                    className="input-field"
                  />
                  <input
                    type="url"
                    placeholder="Instagram Profile URL"
                    value={formInstagram}
                    onChange={(e) => setFormInstagram(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="btn btn-primary"
                >
                  {formSubmitting ? 'Registering...' : 'Register Target'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
