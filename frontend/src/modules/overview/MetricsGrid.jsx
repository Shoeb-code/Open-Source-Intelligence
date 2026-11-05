import React from 'react';
import { Search, ShieldCheck, Globe, Video } from 'lucide-react';

export default function MetricsGrid({ reportData, appearances, sources }) {
  const totalDiscovered = reportData?.statistics?.total_appearances_discovered || appearances.length;
  const verifiedCount =
    reportData?.statistics?.verified_appearances ||
    appearances.filter((a) => a.identity_status === 'VERIFIED').length;
  const distinctSources = reportData?.statistics?.total_distinct_sources || sources.length;
  const topFormat = appearances[0]?.appearance_type || 'Interviews';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Metric 1: Total Discovered */}
      <div className="glass-panel p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Total Discovered</span>
          <Search size={18} className="text-slate-400" />
        </div>
        <div className="text-3xl font-bold mt-2 text-slate-100">{totalDiscovered}</div>
        <p className="text-xs text-slate-400 mt-1">Across public sources & web</p>
      </div>

      {/* Metric 2: Verified Matches */}
      <div className="glass-panel p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Verified Matches</span>
          <ShieldCheck size={18} className="text-emerald-400" />
        </div>
        <div className="text-3xl font-bold mt-2 text-emerald-400">{verifiedCount}</div>
        <p className="text-xs text-slate-400 mt-1">Multi-signal score &gt; 80%</p>
      </div>

      {/* Metric 3: Distinct Sources */}
      <div className="glass-panel p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Distinct Sources</span>
          <Globe size={18} className="text-blue-400" />
        </div>
        <div className="text-3xl font-bold mt-2 text-blue-400">{distinctSources}</div>
        <p className="text-xs text-slate-400 mt-1">Unique URLs & domains</p>
      </div>

      {/* Metric 4: Top Medium */}
      <div className="glass-panel p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Top Medium</span>
          <Video size={18} className="text-pink-400" />
        </div>
        <div className="text-2xl font-bold mt-2 text-pink-400">{topFormat}</div>
        <p className="text-xs text-slate-400 mt-1">Dominant format</p>
      </div>
    </div>
  );
}
