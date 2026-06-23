import React from 'react';

export default function StatCard({ title, value, subtitle, icon, trend, color = 'slate', isFraud = false }) {
  const colorClasses = {
    slate: {
      line: 'bg-slate-500',
      text: 'text-slate-300',
      border: 'border-slate-500/30',
    },
    emerald: {
      line: 'bg-emerald-500',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
    },
    amber: {
      line: 'bg-amber-500',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
    },
    red: {
      line: 'bg-fraud-500',
      text: 'text-fraud-400',
      border: 'border-fraud-500/30',
    },
    gold: {
      line: 'bg-gold-400',
      text: 'text-gold-400',
      border: 'border-gold-500/30',
    },
  };

  const c = colorClasses[color] || colorClasses.slate;

  return (
    <div className={`card relative overflow-hidden ${isFraud ? 'glow-red' : ''}`}>
      {/* Top accent line */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${c.line}`} />

      <div className="card-body">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="stat-label">{title}</p>
            <p className={`stat-value ${c.text}`}>{value}</p>
            {subtitle && (
              <p className="text-xs text-slate-500">{subtitle}</p>
            )}
          </div>
          {icon && (
            <div className={`p-2 rounded-lg bg-slate-700/50 border ${c.border}`}>
              {icon}
            </div>
          )}
        </div>

        {trend !== undefined && (
          <div className="mt-3 flex items-center gap-1.5">
            <svg className={`w-3.5 h-3.5 ${trend >= 0 ? 'text-emerald-400' : 'text-fraud-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d={trend >= 0
                ? 'M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941'
                : 'M2.25 6L9 12.75l4.286-4.286a11.95 11.95 0 015.814 5.519l2.74 1.22m0 0l-5.94 2.28m5.94-2.28l-2.28 5.941'}
              />
            </svg>
            <span className={`text-xs font-medium ${trend >= 0 ? 'text-emerald-400' : 'text-fraud-400'}`}>
              {Math.abs(trend)}% vs last hour
            </span>
          </div>
        )}
      </div>
    </div>
  );
}