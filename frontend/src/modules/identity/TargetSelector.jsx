import React from 'react';
import { User, UserPlus, Trash2, X } from 'lucide-react';

export default function TargetSelector({
  persons,
  selectedPersonId,
  onSelectPerson,
  onOpenRegisterModal,
  onDeletePerson,
  mobileOpen = false,
  onCloseMobile,
}) {
  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden transition-opacity"
        />
      )}

      {/* Responsive Sidebar / Drawer */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-72 sm:w-80 border-r border-slate-800 bg-slate-900/98 backdrop-blur-xl flex flex-col shrink-0 transition-transform duration-300 ease-in-out
          md:static md:translate-x-0 md:z-auto
          ${mobileOpen ? 'translate-x-0 shadow-2xl shadow-cyan-500/10' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User size={18} className="text-cyan-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Target Profiles
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (onCloseMobile) onCloseMobile();
                onOpenRegisterModal();
              }}
              className="btn btn-primary text-xs py-1.5 px-2.5 sm:px-3"
            >
              <UserPlus size={13} />
              <span>New</span>
            </button>

            {/* Mobile Close Button */}
            {onCloseMobile && (
              <button
                onClick={onCloseMobile}
                className="md:hidden text-slate-400 hover:text-white p-1 rounded-lg border border-slate-800 bg-slate-950"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* List of Persons */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {persons.length === 0 ? (
            <div className="py-12 px-4 text-center text-slate-500">
              <User size={36} className="mx-auto mb-3 opacity-30 text-slate-400" />
              <p className="text-xs font-medium text-slate-400">No persons added yet.</p>
              <p className="text-[11px] text-slate-500 mt-1">
                Add someone you want to search public appearances for.
              </p>
              <button
                onClick={() => {
                  if (onCloseMobile) onCloseMobile();
                  onOpenRegisterModal();
                }}
                className="btn btn-secondary text-xs w-full mt-4"
              >
                + Add First Person
              </button>
            </div>
          ) : (
            persons.map((p) => {
              const isSelected = p.id === selectedPersonId;
              return (
                <div
                  key={p.id}
                  onClick={() => {
                    onSelectPerson(p.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`p-3 rounded-lg cursor-pointer transition-all border group relative ${
                    isSelected
                      ? 'border-cyan-500/60 bg-slate-800/90 shadow-md shadow-cyan-500/5'
                      : 'border-transparent hover:bg-slate-800/40 hover:border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className={`text-sm font-semibold truncate ${isSelected ? 'text-sky-400' : 'text-slate-200'}`}>
                      {p.name}
                    </h3>
                    <div className="flex items-center gap-2">
                      {isSelected && (
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />
                      )}
                      {onDeletePerson && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Delete ${p.name} and their search results?`)) {
                              onDeletePerson(p.id);
                            }
                          }}
                          className="opacity-70 md:opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 transition-opacity p-0.5 rounded"
                          title="Delete target"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 mt-0.5 truncate">
                    {p.profession || 'Independent Professional'}
                  </p>

                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {p.social_profiles?.map((sp) => {
                      const isLi = sp.platform === 'linkedin';
                      const isIg = sp.platform === 'instagram';
                      const isYt = sp.platform === 'youtube';
                      const badgeColor = isLi
                        ? 'text-sky-400 border-sky-500/30 bg-sky-500/10'
                        : isIg
                        ? 'text-pink-400 border-pink-500/30 bg-pink-500/10'
                        : isYt
                        ? 'text-rose-400 border-rose-500/30 bg-rose-500/10'
                        : 'text-slate-400 border-slate-800 bg-slate-950/80';

                      return (
                        <span
                          key={sp.id}
                          className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded border ${badgeColor}`}
                        >
                          {sp.platform}
                        </span>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>
    </>
  );
}
