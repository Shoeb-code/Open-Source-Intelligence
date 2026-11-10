import React from 'react';
import { User, UserPlus, Trash2, X, RotateCw } from 'lucide-react';

export default function TargetSelector({
  persons,
  selectedPersonId,
  researchingPersonIds = [],
  onSelectPerson,
  onOpenRegisterModal,
  onDeletePerson,
  mobileOpen = false,
  onCloseMobile,
}) {
  return (
    <>
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-900/35 backdrop-blur-sm z-40 md:hidden transition-opacity"
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-72 sm:w-80 border-r border-slate-200 bg-white flex flex-col shrink-0 transition-transform duration-300 ease-in-out
          md:static md:translate-x-0 md:z-auto
          ${mobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <User size={18} className="text-blue-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              People ({persons.length})
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (onCloseMobile) onCloseMobile();
                onOpenRegisterModal();
              }}
              className="btn btn-primary text-xs py-1.5 px-3"
            >
              <UserPlus size={13} />
              <span>Add Person</span>
            </button>

            {onCloseMobile && (
              <button
                onClick={onCloseMobile}
                className="md:hidden text-slate-500 hover:text-slate-900 p-1 rounded-lg border border-slate-200 bg-slate-50"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* List of People */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5 bg-white">
          {persons.length === 0 ? (
            <div className="py-12 px-4 text-center text-slate-500">
              <User size={36} className="mx-auto mb-3 opacity-35 text-slate-400" />
              <p className="text-xs font-semibold text-slate-700">No people added yet.</p>
              <p className="text-xs text-slate-500 mt-1">
                Add someone to research their public profile and insights.
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
              const isTargetSearching = researchingPersonIds.includes(p.id);
              return (
                <div
                  key={p.id}
                  onClick={() => {
                    onSelectPerson(p.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`p-3 rounded-xl cursor-pointer transition-all border group relative ${
                    isSelected
                      ? 'border-blue-300 bg-blue-50/80 shadow-xs'
                      : 'border-slate-100 bg-white hover:bg-slate-50 hover:border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <h3 className={`text-sm font-semibold truncate ${isSelected ? 'text-blue-700' : 'text-slate-900'}`}>
                      {p.name}
                    </h3>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {isTargetSearching && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
                          <RotateCw size={10} className="animate-spin" />
                          <span>Searching</span>
                        </span>
                      )}
                      {isSelected && !isTargetSearching && (
                        <span className="w-2 h-2 rounded-full bg-blue-600" />
                      )}
                      {onDeletePerson && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Delete ${p.name} and their search results?`)) {
                              onDeletePerson(p.id);
                            }
                          }}
                          className="opacity-70 md:opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 transition-opacity p-0.5 rounded"
                          title="Delete person"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-slate-500 mt-0.5 truncate">
                    {p.profession || 'Independent Professional'}
                  </p>

                  {p.social_profiles?.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      {p.social_profiles.map((sp) => {
                        const isLi = sp.platform === 'linkedin';
                        const isIg = sp.platform === 'instagram';
                        const isYt = sp.platform === 'youtube';
                        const badgeColor = isLi
                          ? 'text-blue-700 border-blue-200 bg-blue-50'
                          : isIg
                          ? 'text-pink-700 border-pink-200 bg-pink-50'
                          : isYt
                          ? 'text-rose-700 border-rose-200 bg-rose-50'
                          : 'text-slate-600 border-slate-200 bg-slate-50';

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
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>
    </>
  );
}
