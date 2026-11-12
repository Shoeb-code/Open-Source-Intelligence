import React from 'react';
import { Search, ShieldCheck, Globe, Video } from 'lucide-react';

export default function MetricsGrid({ reportData, appearances, sources }) {
  const totalDiscovered = reportData?.statistics?.total_appearances_discovered || appearances.length;
  const verifiedCount =
    reportData?.statistics?.verified_appearances ||
    appearances.filter((a) => a.identity_status === 'VERIFIED').length;
  const distinctSources = reportData?.statistics?.total_distinct_sources || sources.length;
  const verifiedPct = totalDiscovered > 0 ? Math.round((verifiedCount / totalDiscovered) * 100) : 0;
  const topFormat = appearances[0]?.appearance_type
    ? appearances[0].appearance_type.replace('_', ' ')
    : 'None yet';
  const extractedCount = sources.filter(
    (s) => s.extraction_status === 'SUCCESS' || s.extraction_status === 'AI_TRANSCRIBED'
  ).length;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs hover:border-slate-300 transition-all">
        <div className="flex justify-between items-center text-slate-500 text-[11px] font-bold uppercase tracking-wider">
          <span className="truncate">Total Found</span>
          <span className="p-1.5 rounded-lg bg-slate-100 text-slate-600 shrink-0 ml-1">
            <Search size={14} />
          </span>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-2 text-slate-900">
          {totalDiscovered}
        </div>
        <p className="text-xs text-slate-500 mt-1 truncate">Consolidated public appearances</p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs hover:border-emerald-200 transition-all">
        <div className="flex justify-between items-center text-slate-500 text-[11px] font-bold uppercase tracking-wider">
          <span className="truncate">Verified Identity</span>
          <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 shrink-0 ml-1 border border-emerald-100">
            <ShieldCheck size={14} />
          </span>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-2 text-emerald-700">
          {verifiedCount}
        </div>
        <p className="text-xs text-slate-500 mt-1 truncate">
          {totalDiscovered > 0 ? `${verifiedPct}% high-confidence (>=80%)` : 'No verified matches yet'}
        </p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs hover:border-blue-200 transition-all">
        <div className="flex justify-between items-center text-slate-500 text-[11px] font-bold uppercase tracking-wider">
          <span className="truncate">Sources Captured</span>
          <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600 shrink-0 ml-1 border border-blue-100">
            <Globe size={14} />
          </span>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-2 text-blue-700">
          {distinctSources}
        </div>
        <p className="text-xs text-slate-500 mt-1 truncate">
          {distinctSources > 0 ? `${extractedCount} with full text/transcript` : 'Unique provenance links'}
        </p>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs hover:border-indigo-200 transition-all">
        <div className="flex justify-between items-center text-slate-500 text-[11px] font-bold uppercase tracking-wider">
          <span className="truncate">Top Format</span>
          <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 shrink-0 ml-1 border border-indigo-100">
            <Video size={14} />
          </span>
        </div>
        <div className="text-lg sm:text-2xl font-extrabold tracking-tight mt-2 text-indigo-700 truncate">
          {topFormat}
        </div>
        <p className="text-xs text-slate-500 mt-1 truncate">Primary appearance format</p>
      </div>
    </div>
  );
}
