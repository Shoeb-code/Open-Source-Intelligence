import React from 'react';
import { User, UserPlus } from 'lucide-react';

export default function TargetSelector({ persons, selectedPersonId, onSelectPerson, onOpenRegisterModal }) {
  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-900/90 flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <User size={18} className="text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Target Profiles
          </h2>
        </div>
        <button
          onClick={onOpenRegisterModal}
          className="btn btn-primary text-xs py-1.5 px-3"
        >
          <UserPlus size={13} />
          <span>New</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {persons.length === 0 ? (
          <div className="py-10 px-4 text-center text-slate-500">
            <User size={32} className="mx-auto mb-3 opacity-30 text-slate-400" />
            <p className="text-xs">No targets registered yet.</p>
            <button
              onClick={onOpenRegisterModal}
              className="btn btn-secondary text-xs w-full mt-3"
            >
              Register First Target
            </button>
          </div>
        ) : (
          persons.map((p) => {
            const isSelected = p.id === selectedPersonId;
            return (
              <div
                key={p.id}
                onClick={() => onSelectPerson(p.id)}
                className={`p-3 rounded-lg cursor-pointer transition-all border ${
                  isSelected
                    ? 'border-cyan-500/60 bg-slate-800/90 shadow-md shadow-cyan-500/5'
                    : 'border-transparent hover:bg-slate-800/40 hover:border-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className={`text-sm font-semibold truncate ${isSelected ? 'text-sky-400' : 'text-slate-200'}`}>
                    {p.name}
                  </h3>
                  {isSelected && (
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5 truncate">
                  {p.profession || 'Independent Professional'}
                </p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {p.social_profiles?.map((sp) => (
                    <span
                      key={sp.id}
                      className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-950/80 text-slate-400 border border-slate-800"
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
  );
}
