import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const POLL_MS  = 2000; // refresh stats every 2s while running

// ── Icons ─────────────────────────────────────────────────────────────────── //
const PlayIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" />
  </svg>
);
const PauseIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
  </svg>
);
const StopIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M6 6h12v12H6z" />
  </svg>
);
const SignalIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.789M12 12h.008v.008H12V12z" />
  </svg>
);

// ── Status config ─────────────────────────────────────────────────────────── //
const STATUS_CFG = {
  stopped:  { label: 'STOPPED',  dot: 'bg-slate-500',                ring: 'ring-slate-500/20' },
  running:  { label: 'LIVE',     dot: 'bg-emerald-400 animate-pulse', ring: 'ring-emerald-500/20' },
  paused:   { label: 'PAUSED',   dot: 'bg-amber-400',                ring: 'ring-amber-500/20' },
  loading:  { label: '...',      dot: 'bg-slate-600 animate-pulse',  ring: 'ring-slate-600/20' },
};

const RATES = [0.5, 1, 2, 3, 5];

export default function SimulationControl() {
  const [simState, setSimState]   = useState('stopped'); // stopped | running | paused
  const [stats, setStats]         = useState({ sent: 0, fraud: 0, rate: 1.0, started_at: null });
  const [rate, setRate]           = useState(1.0);
  const [busy, setBusy]           = useState(false);    // button in-flight
  const pollRef                   = useRef(null);
  const mountedRef                = useRef(true);

  // ── Fetch current status from backend ──────────────────────────────────── //
  const fetchStatus = useCallback(async () => {
    try {
      const res  = await fetch(`${API_BASE}/api/simulate/status`);
      if (!res.ok) return;
      const data = await res.json();
      if (!mountedRef.current) return;

      const next = data.paused ? 'paused' : data.running ? 'running' : 'stopped';
      setSimState(next);
      setStats({
        sent:       data.sent       ?? 0,
        fraud:      data.fraud      ?? 0,
        rate:       data.rate       ?? rate,
        started_at: data.started_at ?? null,
      });
    } catch { /* server not reachable — keep current state */ }
  }, [rate]);

  // ── Polling while running or paused ───────────────────────────────────── //
  useEffect(() => {
    fetchStatus(); // initial check
  }, [fetchStatus]);

  useEffect(() => {
    clearInterval(pollRef.current);
    if (simState === 'running' || simState === 'paused') {
      pollRef.current = setInterval(fetchStatus, POLL_MS);
    }
    return () => clearInterval(pollRef.current);
  }, [simState, fetchStatus]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearInterval(pollRef.current);
    };
  }, []);

  // ── Actions ───────────────────────────────────────────────────────────── //
  const call = useCallback(async (endpoint, method = 'POST') => {
    setBusy(true);
    try {
      const res  = await fetch(`${API_BASE}/api/simulate/${endpoint}`, { method });
      const data = await res.json();
      if (!mountedRef.current) return;
      const next = data.paused ? 'paused' : data.running ? 'running' : 'stopped';
      setSimState(next);
      setStats({
        sent:       data.sent       ?? 0,
        fraud:      data.fraud      ?? 0,
        rate:       data.rate       ?? rate,
        started_at: data.started_at ?? null,
      });
    } catch (e) {
      console.error('Simulation API error:', e);
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }, [rate]);

  const handleStart  = () => call(`start?rate=${rate}`);
  const handleStop   = () => call('stop');
  const handlePause  = () => call('pause');
  const handleResume = () => call('resume');

  // ── Derived display ───────────────────────────────────────────────────── //
  const cfg        = STATUS_CFG[busy ? 'loading' : simState] ?? STATUS_CFG.stopped;
  const isRunning  = simState === 'running';
  const isPaused   = simState === 'paused';
  const isStopped  = simState === 'stopped';
  const fraudPct   = stats.sent > 0 ? ((stats.fraud / stats.sent) * 100).toFixed(1) : '0.0';

  const elapsed = (() => {
    if (!stats.started_at || isStopped) return null;
    const secs = Math.floor((Date.now() - new Date(stats.started_at).getTime()) / 1000);
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  })();

  return (
    <div className="card h-full flex flex-col">
      {/* Header */}
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SignalIcon />
          <h2 className="text-sm font-semibold text-slate-200">Simulation Control</h2>
        </div>
        {/* Status pill */}
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full ring-1 ${cfg.ring} bg-slate-800/60`}>
          <div className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          <span className="text-[10px] font-mono text-slate-400">{cfg.label}</span>
        </div>
      </div>

      <div className="card-body flex flex-col gap-4">

        {/* Rate selector — only editable when stopped */}
        <div>
          <p className="text-[10px] text-slate-500 font-mono mb-2 uppercase tracking-wider">
            Tx / second
          </p>
          <div className="flex gap-1.5">
            {RATES.map(r => (
              <button
                key={r}
                disabled={!isStopped || busy}
                onClick={() => setRate(r)}
                className={`flex-1 py-1.5 rounded-md text-xs font-mono font-medium transition-all ${
                  rate === r
                    ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40'
                    : 'bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          {!isStopped && (
            <p className="text-[10px] text-slate-600 mt-1.5 font-mono">
              Running at {stats.rate} tx/s — stop to change rate
            </p>
          )}
        </div>

        {/* Control buttons */}
        <div className="flex gap-2">
          {/* Start / Resume */}
          {(isStopped || isPaused) && (
            <button
              disabled={busy}
              onClick={isPaused ? handleResume : handleStart}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg
                         bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400
                         ring-1 ring-emerald-500/30 hover:ring-emerald-500/50
                         text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlayIcon />
              {isPaused ? 'Resume' : 'Start'}
            </button>
          )}

          {/* Pause */}
          {isRunning && (
            <button
              disabled={busy}
              onClick={handlePause}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg
                         bg-amber-500/15 hover:bg-amber-500/25 text-amber-400
                         ring-1 ring-amber-500/30 hover:ring-amber-500/50
                         text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PauseIcon />
              Pause
            </button>
          )}

          {/* Stop */}
          {(isRunning || isPaused) && (
            <button
              disabled={busy}
              onClick={handleStop}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg
                         bg-red-500/15 hover:bg-red-500/25 text-red-400
                         ring-1 ring-red-500/30 hover:ring-red-500/50
                         text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <StopIcon />
              Stop
            </button>
          )}
        </div>

        {/* Live stats — only show when active */}
        {!isStopped && (
          <div className="grid grid-cols-3 gap-2 pt-1">
            <StatBox label="Sent"      value={stats.sent.toLocaleString()} />
            <StatBox label="Fraud"     value={stats.fraud.toLocaleString()} accent="text-red-400" />
            <StatBox label="Fraud %"   value={`${fraudPct}%`}
              accent={parseFloat(fraudPct) > 5 ? 'text-red-400' : 'text-slate-300'} />
          </div>
        )}

        {elapsed && (
          <p className="text-[10px] text-slate-600 font-mono text-center -mt-1">
            Running for {elapsed}
          </p>
        )}

      </div>
    </div>
  );
}

function StatBox({ label, value, accent = 'text-slate-200' }) {
  return (
    <div className="bg-slate-800/60 rounded-lg p-2.5 text-center">
      <p className={`text-sm font-mono font-semibold ${accent}`}>{value}</p>
      <p className="text-[10px] text-slate-600 mt-0.5">{label}</p>
    </div>
  );
}