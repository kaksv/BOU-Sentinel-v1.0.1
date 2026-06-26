import React, { useState } from 'react';

export default function FraudHeatmap({ activityData = [] }) {
  const [selected, setSelected] = useState(null);

  const sortedData = [...activityData].sort((a, b) => new Date(a.minute) - new Date(b.minute));
const fraudItems = sortedData.filter(item => (item.fraud || 0) > 0);

  return (
    <div className="card h-full">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Fraud Activity Map</h2>
        <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">
          Last 30 min
        </span>
      </div>

      <div className="card-body">
        {sortedData.length === 0 ? (
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
              {sortedData.slice(0, 24).map((item, i) => {
                const fraud = item.fraud || 0;
                const total = item.total || 1;
                const intensity = Math.min(fraud / Math.max(total * 0.2, 1), 1);
                const isSelected = selected === i;

                return (
                  <div key={i} className="group relative">
                    <div
                    onClick={() => setSelected(isSelected ? null : i)}
                      className={`w-full aspect-square rounded-md transition-all duration-300 cursor-pointer border-2 ${
                        isSelected ? 'border-white/40 scale-110' : 'border-transparent'
                      }  ${
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
                      {item.minute
                        ? new Date(item.minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : `Slot ${i + 1}`}
                      {' • '}{total} txns • {fraud} fraud
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between text-[10px] text-slate-500 mb-4">
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

            {/* Selected cell detail */}
            {selected !== null && sortedData[selected] && (
              <>
                <div className="mb-4 p-3 rounded-lg bg-slate-800/60 border border-slate-700 text-[11px] font-mono">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-300 font-semibold">
                      Slot {selected + 1} —{' '}
                      {sortedData[selected].minute
                        ? new Date(sortedData[selected].minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : 'N/A'}
                    </span>
                    <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-300">✕</button>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    {/* <div className="bg-slate-700/40 rounded p-2">
                      <div className="text-slate-400">Total</div>
                      <div className="text-slate-200 font-bold">{sortedData[selected].total || 0}</div>
                    </div> */}
                    <div className="bg-red-900/30 rounded p-2">
                      <div className="text-slate-400">Frauds</div>
                      <div className="text-red-400 font-bold">{sortedData[selected].fraud || 0}</div>
                    </div>
                    <div className="bg-slate-700/40 rounded p-2">
                      <div className="text-slate-400">Rate</div>
                      <div className="text-amber-400 font-bold">
                        {sortedData[selected].total
                          ? ((sortedData[selected].fraud / sortedData[selected].total) * 100).toFixed(1)
                          : 0}%
                      </div>
                    </div>
                  </div>
                </div>
                {/* Fraud activity feed */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
                      Fraud Activity Feed
                    </span>
                    <span className="text-[10px] text-red-400 font-mono">
                      flagged transactions
                    </span>
                  </div>

                  {fraudItems.length === 0 ? (
                    <div className="text-center py-4 text-[11px] text-slate-500">
                      ✅ No fraud detected in this window
                    </div>
                  ) : (
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {fraudItems.map((item, i) => {
                        const rate = item.total
                          ? ((item.fraud / item.total) * 100).toFixed(1)
                          : 0;
                        const isCritical = rate > 60;
                        const isModerate = rate > 30 && rate <= 60;

                        return (
                          <div
                            key={i}
                            className={`flex items-center justify-between px-3 py-1.5 rounded-md text-[10px] font-mono border ${
                              isCritical
                                ? 'bg-red-900/20 border-red-800/40 text-red-300'
                                : isModerate
                                ? 'bg-amber-900/20 border-amber-800/40 text-amber-300'
                                : 'bg-slate-800/40 border-slate-700/40 text-slate-400'
                            }`}
                          >
                            <span>
                              {item.minute
                                ? new Date(item.minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                : `Slot ${i + 1}`}
                            </span>
                            <span>{item.id} transactions</span>
                            <span className="flex items-center gap-1">
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${
                                  isCritical ? 'bg-red-400' : isModerate ? 'bg-amber-400' : 'bg-emerald-400'
                                }`}
                              />
                              {item.fraud}    ({rate}%)
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}

          </>
        )}
      </div>
    </div>
  );
}