import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws';

// How long after the last transaction event to wait before re-fetching stats.
// Batches rapid bursts into a single request.
const DEBOUNCE_MS = 800;

export default function RiskScoreGauge({ riskScore: propScore = 0, transactionCount: propCount = 0 }) {
  const [riskScore, setRiskScore]           = useState(propScore);
  const [transactionCount, setTransactionCount] = useState(propCount);
  const [fraudCount, setFraudCount]         = useState(0);
  const [fraudRate, setFraudRate]           = useState(0);
  const [loading, setLoading]               = useState(true);
  const [lastUpdated, setLastUpdated]       = useState(null);

  const mountedRef  = useRef(true);
  const wsRef       = useRef(null);
  const retryRef    = useRef(null);
  const debounceRef = useRef(null);

  // ── Fetch /api/stats ──────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!mountedRef.current) return;

      setRiskScore(data.avg_risk_score ?? 0);
      setTransactionCount(data.total_transactions ?? 0);
      setFraudCount(data.fraud_transactions ?? 0);
      setFraudRate(data.fraud_rate ?? 0);
      setLastUpdated(new Date());
    } catch {
      // Keep previous values on error — gauge stays visible
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  // Debounced version triggered by WS events — batches rapid inflows
  const debouncedFetch = useCallback(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchStats, DEBOUNCE_MS);
  }, [fetchStats]);

  // ── WebSocket (triggers stats refresh on each new transaction) ────────────
  const connectWs = useCallback(() => {
    if (!mountedRef.current) return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'transaction' || (!msg.type && msg.transaction_id)) {
          debouncedFetch();
        }
      } catch { /* pong / plain text */ }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      retryRef.current = setTimeout(connectWs, 3000);
    };
  }, [debouncedFetch]);

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    fetchStats();
    connectWs();
    return () => {
      mountedRef.current = false;
      clearTimeout(retryRef.current);
      clearTimeout(debounceRef.current);
      wsRef.current?.close();
    };
  }, [fetchStats, connectWs]);

  // ── Derived display values ────────────────────────────────────────────────
  const percentage = Math.round(riskScore * 100);
  const angle      = riskScore * 180; // 0 → 180 °

  const color = riskScore > 0.75 ? '#ef4444'
    : riskScore > 0.5            ? '#f59e0b'
    : riskScore > 0.25           ? '#eab308'
    :                              '#10b981';

  const label = riskScore > 0.75 ? 'CRITICAL'
    : riskScore > 0.5            ? 'ELEVATED'
    : riskScore > 0.25           ? 'MODERATE'
    :                              'LOW';

  const dotClass = riskScore > 0.75 ? 'bg-red-500 animate-pulse'
    : riskScore > 0.5              ? 'bg-amber-500'
    :                                'bg-emerald-500';

  const updatedLabel = lastUpdated
    ? lastUpdated.toLocaleTimeString('en-UG', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  return (
    <div className="card h-full">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">AI Risk Score Gauge</h2>
        {updatedLabel && !loading && (
          <span className="text-[10px] text-slate-600 font-mono">
            Updated {updatedLabel}
          </span>
        )}
      </div>

      <div className="card-body flex flex-col items-center justify-center py-6">

        {/* ── SVG Gauge ───────────────────────────────────────────────────── */}
        <div className="relative w-48 h-36">
          {loading ? (
            /* Skeleton while first fetch resolves */
            <svg className="w-full h-full" viewBox="0 0 200 160">
              <path d="M 20 140 A 80 80 0 0 1 180 140" fill="none" stroke="#334155" strokeWidth="20" strokeLinecap="round" />
              <circle cx="100" cy="140" r="6" fill="#334155" />
              <circle cx="100" cy="140" r="3" fill="#1e293b" stroke="#475569" strokeWidth="2" />
            </svg>
          ) : (
            <svg className="w-full h-full" viewBox="0 0 200 160">
              {/* Track */}
              <path d="M 20 140 A 80 80 0 0 1 180 140" fill="none" stroke="#334155" strokeWidth="20" strokeLinecap="round" />

              {/* Zone ticks */}
              {[0.25, 0.5, 0.75].map((pct) => {
                const rad = Math.PI - pct * Math.PI;
                const r = 80;
                const cx = 100 + r * Math.cos(rad);
                const cy = 140 - r * Math.sin(rad);
                return <circle key={pct} cx={cx} cy={cy} r="3" fill="#1e293b" />;
              })}

              {/* Filled arc */}
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
              <g
                className="transition-all duration-1000 ease-out"
                style={{ transform: `rotate(${angle - 90}deg)`, transformOrigin: '100px 140px' }}
              >
                <line x1="100" y1="140" x2="100" y2="58" stroke="#e2e8f0" strokeWidth="2.5" strokeLinecap="round" />
                <circle cx="100" cy="140" r="6" fill={color} />
              </g>

              {/* Center pip */}
              <circle cx="100" cy="140" r="3" fill="#1e293b" stroke="#475569" strokeWidth="2" />

              {/* Arc labels */}
              <text x="18"  y="118" fontSize="9" fill="#64748b" textAnchor="middle">LOW</text>
              <text x="100" y="158" fontSize="9" fill="#64748b" textAnchor="middle">RISK</text>
              <text x="182" y="118" fontSize="9" fill="#64748b" textAnchor="middle">HIGH</text>
            </svg>
          )}
        </div>

        {/* ── Score readout ────────────────────────────────────────────────── */}
        <div className="text-center mt-4">
          {loading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="h-10 w-20 rounded bg-slate-700 animate-pulse" />
              <div className="h-3 w-16 rounded bg-slate-800 animate-pulse" />
            </div>
          ) : (
            <>
              <div className="flex items-baseline justify-center gap-2">
                <span
                  className="text-4xl font-bold font-mono tracking-tight transition-all duration-1000"
                  style={{ color }}
                >
                  {percentage}
                </span>
                <span className="text-sm text-slate-400 font-medium">/ 100</span>
              </div>
              <div className="flex items-center justify-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${dotClass}`} />
                <span className="text-xs font-semibold tracking-wider" style={{ color }}>
                  {label}
                </span>
              </div>
            </>
          )}
        </div>

        {/* ── Secondary stats row ──────────────────────────────────────────── */}
        {!loading && (
          <div className="flex items-center gap-4 mt-5 pt-4 border-t border-slate-800 w-full justify-center">
            <Stat label="Transactions" value={transactionCount.toLocaleString()} />
            <div className="w-px h-6 bg-slate-800" />
            <Stat label="Fraud Flagged" value={fraudCount.toLocaleString()} accent="text-red-400" />
            <div className="w-px h-6 bg-slate-800" />
            <Stat label="Fraud Rate" value={`${fraudRate.toFixed(1)}%`} accent={fraudRate > 5 ? 'text-red-400' : 'text-slate-300'} />
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, accent = 'text-slate-300' }) {
  return (
    <div className="text-center">
      <p className={`text-sm font-mono font-semibold ${accent}`}>{value}</p>
      <p className="text-[10px] text-slate-600 mt-0.5">{label}</p>
    </div>
  );
}