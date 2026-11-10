import React, { useState, useEffect, useRef } from 'react';
import {
  Download,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  FileCode,
  Users,
  RotateCw,
} from 'lucide-react';

export default function DownloadMenu({
  personName,
  onDownloadPerson,
  onDownloadAll = null,
  personsCount = 1,
  disabled = false,
  buttonLabel = 'Download Report',
  buttonClassName = 'btn btn-secondary text-xs sm:text-sm',
}) {
  const [open, setOpen] = useState(false);
  const [exportingAll, setExportingAll] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!open || typeof document === 'undefined') return undefined;

    function handleOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    function handleKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }

    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  function handlePersonClick(format) {
    setOpen(false);
    if (onDownloadPerson) onDownloadPerson(format);
  }

  async function handleAllClick(format) {
    if (!onDownloadAll || exportingAll) return;
    setExportingAll(true);
    try {
      await onDownloadAll(format);
    } finally {
      setExportingAll(false);
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled || exportingAll}
        className={`${buttonClassName} disabled:opacity-50 disabled:cursor-not-allowed`}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {exportingAll ? (
          <RotateCw size={15} className="animate-spin text-blue-600" />
        ) : (
          <Download size={15} className="text-blue-600" />
        )}
        <span>{exportingAll ? 'Preparing Export...' : buttonLabel}</span>
        <ChevronDown size={13} className="text-slate-400" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-64 rounded-xl bg-white border border-slate-200 shadow-lg z-50 py-1.5 text-left"
        >
          <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400 truncate">
            {personName ? `Export: ${personName}` : 'Current Person'}
          </div>

          <button
            type="button"
            role="menuitem"
            onClick={() => handlePersonClick('csv')}
            className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
          >
            <FileSpreadsheet size={15} className="text-emerald-600 shrink-0" />
            <div>
              <div className="font-semibold">Excel Spreadsheet (.csv)</div>
              <div className="text-[11px] text-slate-400">Profile, insights & appearances</div>
            </div>
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => handlePersonClick('md')}
            className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
          >
            <FileText size={15} className="text-blue-600 shrink-0" />
            <div>
              <div className="font-semibold">Manager Briefing (.md)</div>
              <div className="text-[11px] text-slate-400">Formatted readable report</div>
            </div>
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => handlePersonClick('json')}
            className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
          >
            <FileCode size={15} className="text-indigo-600 shrink-0" />
            <div>
              <div className="font-semibold">Structured Data (.json)</div>
              <div className="text-[11px] text-slate-400">Full API JSON export</div>
            </div>
          </button>

          {onDownloadAll && personsCount > 1 && (
            <>
              <div className="my-1.5 border-t border-slate-100" />
              <div className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Users size={11} />
                <span>All {personsCount} People</span>
              </div>

              <button
                type="button"
                role="menuitem"
                onClick={() => handleAllClick('csv')}
                className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
              >
                <FileSpreadsheet size={15} className="text-emerald-600 shrink-0" />
                <span className="font-semibold">All People Excel (.csv)</span>
              </button>

              <button
                type="button"
                role="menuitem"
                onClick={() => handleAllClick('md')}
                className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
              >
                <FileText size={15} className="text-blue-600 shrink-0" />
                <span className="font-semibold">All People Briefing (.md)</span>
              </button>

              <button
                type="button"
                role="menuitem"
                onClick={() => handleAllClick('json')}
                className="w-full px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2.5 transition-colors"
              >
                <FileCode size={15} className="text-indigo-600 shrink-0" />
                <span className="font-semibold">All People Data (.json)</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

