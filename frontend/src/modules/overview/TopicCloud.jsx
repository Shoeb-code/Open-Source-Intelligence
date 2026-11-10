import React from 'react';
import { TrendingUp } from 'lucide-react';

export default function TopicCloud({ topics }) {
  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
      <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
        <TrendingUp size={16} className="text-blue-600" />
        <span>Recurring Topics & Themes</span>
      </h4>
      <div className="flex flex-wrap gap-2">
        {topics && topics.length > 0 ? (
          topics.map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-50 border border-slate-200 text-slate-700 hover:border-blue-300 transition-colors"
            >
              <span>{t.topic}</span>
              <span className="text-blue-700 font-semibold text-[11px]">{t.count}</span>
            </span>
          ))
        ) : (
          <p className="text-xs text-slate-500">Topics will appear here after discovery.</p>
        )}
      </div>
    </div>
  );
}
