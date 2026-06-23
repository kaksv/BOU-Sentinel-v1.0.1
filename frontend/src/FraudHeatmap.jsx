import React from 'react';

export default function FraudHeatmap({ activityData = [] }) {
  return (
    <div className="card h-full">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Fraud Activity Map</h2>
        <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">
          Last 30 min
        </span>
      </div>

      <div className="card-body">
        {activityData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <svg className="w-10 h-10 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <p className="text-sm text-slate-500">No activity data yet</p>
          </div>
        ) : (
          <>
            {/* Heatmap cells */}
            <div className="grid grid-cols-8 gap-1.5 mb-4">
              {activityData.slice(0, 24).map((item, i) => {
                const fraud = item.fraud || 0;
                const total = item.total || 1;
                const intensity = Math.min(fraud / Math.max(total * 0.2, 1), 1);

                return (
                  <div key={i} className="group relative">
                    <div
                      className={`w-full aspect-square rounded-md transition-all duration-300 ${
                        intensity === 0
                          ? 'bg-slate-700/30'
                          : intensity > 0.6
                          ? 'bg-fraud-600/80'
                          : intensity > 0.3
                          ? 'bg-amber-600/60'
                          : 'bg-emerald-600/40'
                      }`}
                      style={{
                        opacity: 0.3 + intensity * 0.7,
                      }}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 rounded bg-slate-700 text-[10px] text-slate-200 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 shadow-lg">
                      {total} txns • {fraud} fraud
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between text-[10px] text-slate-500">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-emerald-600/40" />
                <span>Low Risk</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-600/60" />
                <span>Moderate</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-fraud-600/80" />
                <span>Critical</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}