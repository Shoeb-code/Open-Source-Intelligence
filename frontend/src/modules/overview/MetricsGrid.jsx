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
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Total Found</span>
          <Search size={15} className="text-slate-400 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-2 text-slate-900">{totalDiscovered}</div>
        <p className="text-xs text-slate-500 mt-1 truncate">Public appearances</p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Verified</span>
          <ShieldCheck size={15} className="text-emerald-600 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-2 text-emerald-700">{verifiedCount}</div>
        <p className="text-xs text-slate-500 mt-1 truncate">Score &gt; 80%</p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Sources</span>
          <Globe size={15} className="text-blue-600 shrink-0 ml-1" />
        </div>
        <div className="text-2xl sm:text-3xl font-bold mt-2 text-blue-700">{distinctSources}</div>
        <p className="text-xs text-slate-500 mt-1 truncate">Unique links</p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase tracking-wider">
          <span className="truncate">Top Format</span>
          <Video size={15} className="text-pink-600 shrink-0 ml-1" />
        </div>
        <div className="text-lg sm:text-2xl font-bold mt-2 text-pink-700 truncate">{topFormat}</div>
        <p className="text-xs text-slate-500 mt-1 truncate">Most frequent</p>
      </div>
    </div>
  );
}
