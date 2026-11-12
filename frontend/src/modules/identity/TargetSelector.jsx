import React, { useMemo, useState } from 'react';
import { User, UserPlus, Trash2, X, RotateCw, Search, CheckCircle2 } from 'lucide-react';

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
  const [query, setQuery] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const filteredPersons = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return persons;
    return persons.filter((p) => {
      const nameMatch = p.name?.toLowerCase().includes(q);
      const profMatch = p.profession?.toLowerCase().includes(q);
      const platMatch = p.social_profiles?.some((sp) => sp.platform?.toLowerCase().includes(q));
      return nameMatch || profMatch || platMatch;
    });
  }, [persons, query]);

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
        <div className="p-4 border-b border-slate-200 space-y-3 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                <User size={15} />
              </span>
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
                  aria-label="Close sidebar"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {persons.length > 0 && (
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter people or roles..."
                className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 transition-all"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                  aria-label="Clear filter"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          )}
        </div>

        {/* List of People */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50/40">
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
          ) : filteredPersons.length === 0 ? (
            <div className="py-10 px-4 text-center text-xs text-slate-500">
              No targets match &ldquo;{query}&rdquo;.
            </div>
          ) : (
            filteredPersons.map((p) => {
              const isSelected = p.id === selectedPersonId;
              const isTargetSearching = researchingPersonIds.includes(p.id);
              const isEnriched = p.enrichment_status === 'SUCCESS' && Boolean(p.profile_enriched_at);
              const isConfirming = confirmDeleteId === p.id;
              const initials = (p.name || '?')
                .split(' ')
                .map((n) => n[0])
                .join('')
                .toUpperCase()
                .slice(0, 2);

              return (
                <div
                  key={p.id}
                  onClick={() => {
                    setConfirmDeleteId(null);
                    onSelectPerson(p.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`p-3 rounded-xl cursor-pointer transition-all border group relative ${
                    isSelected
                      ? 'border-blue-300 bg-white shadow-sm ring-1 ring-blue-500/10'
                      : 'border-slate-200/80 bg-white/80 hover:bg-white hover:border-slate-300'
                  }`}
                >
                  {isSelected && (
                    <span className="absolute left-0 top-2.5 bottom-2.5 w-1 rounded-r-full bg-blue-600" />
                  )}

                  <div className="flex items-start gap-2.5">
                    <div
                      className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-xs font-bold border ${
                        isSelected
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {initials}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1.5">
                        <h3
                          className={`text-sm font-semibold truncate ${
                            isSelected ? 'text-blue-700' : 'text-slate-900'
                          }`}
                        >
                          {p.name}
                        </h3>

                        <div className="flex items-center gap-1 shrink-0">
                          {isTargetSearching && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                              <RotateCw size={9} className="animate-spin" />
                              <span>Live</span>
                            </span>
                          )}
                          {isEnriched && !isTargetSearching && (
                            <CheckCircle2
                              size={13}
                              className="text-emerald-600"
                              title="LinkedIn Profile Enriched"
                            />
                          )}
                          {onDeletePerson && !isConfirming && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmDeleteId(p.id);
                              }}
                              className="opacity-70 md:opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 transition-opacity p-0.5 rounded"
                              title="Delete person"
                              aria-label={`Delete ${p.name}`}
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </div>

                      <p className="text-xs text-slate-500 mt-0.5 truncate">
                        {p.profession || 'Independent Professional'}
                      </p>

                      {isConfirming ? (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className="mt-2 flex items-center gap-1.5 text-[11px]"
                        >
                          <button
                            type="button"
                            onClick={() => {
                              setConfirmDeleteId(null);
                              onDeletePerson(p.id);
                            }}
                            className="px-2 py-0.5 rounded bg-rose-600 text-white font-semibold hover:bg-rose-700"
                          >
                            Confirm Delete
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(null)}
                            className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 hover:bg-slate-200"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        p.social_profiles?.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1 mt-2">
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
                        )
                      )}
                    </div>
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
