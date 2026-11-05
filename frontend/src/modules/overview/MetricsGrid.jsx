import React from 'react';
import { Search, ShieldCheck, Globe, Video } from 'lucide-react';

export default function MetricsGrid({ reportData, appearances, sources }) {
  const totalDiscovered = reportData?.statistics?.total_appearances_discovered || appearances.length;
  const verifiedCount =
    reportData?.statistics?.verified_appearances ||
    appearances.filter((a) => a.identity_status === 'VERIFIED').length;
  const distinctSources = reportData?.statistics?.total_distinct_sources || sources.length;
  const topFormat = appearances[0]?.appearance_type ? appearances[0].appearance_type.replace('_', ' ') : 'None yet';

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4">
      {/* Metric 1: Total Discovered */}
      <div className="glass-panel p-3.5 sm:p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-[10px] sm:text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Total Found</span>
          <Search size={15} className="text-slate-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-1.5 sm:mt-2 text-slate-100">{totalDiscovered}</div>
        <p className="text-[10px] sm:text-xs text-slate-400 mt-0.5 sm:mt-1 truncate">Public appearances</p>
      </div>

      {/* Metric 2: Verified Matches */}
      <div className="glass-panel p-3.5 sm:p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-[10px] sm:text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Verified</span>
          <ShieldCheck size={15} className="text-emerald-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-1.5 sm:mt-2 text-emerald-400">{verifiedCount}</div>
        <p className="text-[10px] sm:text-xs text-slate-400 mt-0.5 sm:mt-1 truncate">Score &gt; 80%</p>
      </div>

      {/* Metric 3: Distinct Sources */}
      <div className="glass-panel p-3.5 sm:p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-[10px] sm:text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Sources</span>
          <Globe size={15} className="text-blue-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-1.5 sm:mt-2 text-blue-400">{distinctSources}</div>
        <p className="text-[10px] sm:text-xs text-slate-400 mt-0.5 sm:mt-1 truncate">Unique domains</p>
      </div>

      {/* Metric 4: Top Medium */}
      <div className="glass-panel p-3.5 sm:p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-md">
        <div className="flex justify-between items-center text-slate-400 text-[10px] sm:text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Top Medium</span>
          <Video size={15} className="text-pink-400 shrink-0 ml-1" />
        </div>
        <div className="text-lg sm:text-2xl font-bold mt-1.5 sm:mt-2 text-pink-400 truncate">{topFormat}</div>
        <p className="text-[10px] sm:text-xs text-slate-400 mt-0.5 sm:mt-1 truncate">Dominant format</p>
      </div>
    </div>
  );
}
