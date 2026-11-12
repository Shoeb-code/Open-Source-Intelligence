import React from 'react';
import { TrendingUp } from 'lucide-react';

export default function TopicCloud({ topics }) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
      <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
        <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
          <TrendingUp size={15} />
        </span>
        <span>Recurring Topics &amp; Themes</span>
      </h4>
      <div className="flex flex-wrap gap-2">
        {topics && topics.length > 0 ? (
          topics.map((t, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-50 border border-slate-200 text-slate-700 hover:border-blue-300 hover:bg-blue-50/40 transition-colors"
            >
              <span>{t.topic}</span>
              <span className="px-1.5 py-0.5 rounded-full bg-white border border-slate-200 text-blue-700 font-bold text-[10px]">
                {t.count}
              </span>
            </span>
          ))
        ) : (
          <p className="text-xs text-slate-500">Topics will appear here after discovery.</p>
        )}
      </div>
    </div>
  );
}
