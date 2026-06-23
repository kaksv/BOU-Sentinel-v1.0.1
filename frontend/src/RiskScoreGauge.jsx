import React from 'react';

export default function RiskScoreGauge({ riskScore = 0, transactionCount = 0 }) {
  // riskScore is 0.0 to 1.0
  const percentage = Math.round(riskScore * 100);
  const angle = (riskScore * 180); // 0 to 180 degrees

  // Color based on risk level
  const color = riskScore > 0.75
    ? '#ef4444'
    : riskScore > 0.5
    ? '#f59e0b'
    : riskScore > 0.25
    ? '#eab308'
    : '#10b981';

  const label = riskScore > 0.75
    ? 'CRITICAL'
    : riskScore > 0.5
    ? 'ELEVATED'
    : riskScore > 0.25
    ? 'MODERATE'
    : 'LOW';

  return (
    <div className="card h-full">
      <div className="card-header">
        <h2 className="text-sm font-semibold text-slate-200">AI Risk Score Gauge</h2>
      </div>
      <div className="card-body flex flex-col items-center justify-center py-6">
        {/* SVG Gauge */}
        <div className="relative w-48 h-36">
          <svg className="w-full h-full" viewBox="0 0 200 160">
            {/* Background arc */}
            <path
              d="M 20 140 A 80 80 0 0 1 180 140"
              fill="none"
              stroke="#334155"
              strokeWidth="20"
              strokeLinecap="round"
            />

            {/* Colored arc */}
            <path
              d="M 20 140 A 80 80 0 0 1 180 140"
              fill="none"
              stroke={color}
              strokeWidth="20"
              strokeLinecap="round"
              strokeDasharray={`${(riskScore * 251.2).toFixed(1)} 251.2`}
              className="transition-all duration-1000 ease-out"
            />

            {/* Needle */}
            <g className="transition-all duration-1000 ease-out"
               style={{ transform: `rotate(${angle - 90}deg)`, transformOrigin: '100px 140px' }}>
              <line x1="100" y1="140" x2="100" y2="55" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
              <circle cx="100" cy="140" r="6" fill={color} />
            </g>

            {/* Center dot */}
            <circle cx="100" cy="140" r="3" fill="#1e293b" stroke="#475569" strokeWidth="2" />

            {/* Labels */}
            <text x="25" y="120" className="text-[10px] fill-slate-500" textAnchor="middle">LOW</text>
            <text x="100" y="155" className="text-[10px] fill-slate-500" textAnchor="middle">RISK</text>
            <text x="175" y="120" className="text-[10px] fill-slate-500" textAnchor="middle">HIGH</text>
          </svg>
        </div>

        {/* Score display */}
        <div className="text-center mt-4">
          <div className="flex items-baseline justify-center gap-2">
            <span className="text-4xl font-bold font-mono tracking-tight" style={{ color }}>
              {percentage}
            </span>
            <span className="text-sm text-slate-400 font-medium">/ 100</span>
          </div>
          <div className="flex items-center justify-center gap-2 mt-1">
            <div className={`w-2 h-2 rounded-full ${
              riskScore > 0.75 ? 'bg-fraud-500 animate-siren' :
              riskScore > 0.5 ? 'bg-amber-500' :
              'bg-emerald-500'
            }`} />
            <span className="text-xs font-semibold tracking-wider" style={{ color }}>
              {label}
            </span>
          </div>
        </div>

        {/* Mini transaction count */}
        <p className="text-[10px] text-slate-600 mt-4 font-mono">
          Based on {transactionCount || 0} analyzed transactions
        </p>
      </div>
    </div>
  );
}