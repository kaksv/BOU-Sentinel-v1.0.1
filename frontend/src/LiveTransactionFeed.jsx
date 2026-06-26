import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws';
const MAX_FEED  = 100;

// ── Formatters ────────────────────────────────────────────────────────────── //
const fmtUGX = (n) =>
  new Intl.NumberFormat('en-UG', { style: 'currency', currency: 'UGX', minimumFractionDigits: 0 }).format(n);

const fmtTime = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-UG', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
};

// ── Main component ────────────────────────────────────────────────────────── //
export default function LiveTransactionFeed({ transactions: propTransactions = [] }) {
  const [transactions, setTransactions] = useState([]);
  const [wsStatus, setWsStatus]         = useState('connecting');
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [selected, setSelected]         = useState(null);

  const wsRef      = useRef(null);
  const retryRef   = useRef(null);
  const mountedRef = useRef(true);

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res  = await fetch(`${API_BASE}/api/transactions?limit=50`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (mountedRef.current) setTransactions(data.slice(0, MAX_FEED));
    } catch (err) {
      if (mountedRef.current) setError(err.message);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  const connectWs = useCallback(() => {
    if (!mountedRef.current) return;
    setWsStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen  = () => { if (mountedRef.current) setWsStatus('live'); };
    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'transaction' || (!msg.type && msg.transaction_id)) {
          setTransactions(prev => [msg, ...prev].slice(0, MAX_FEED));
        }
      } catch { /* pong/plain text */ }
    };
    ws.onclose = () => {
      if (!mountedRef.current) return;
      setWsStatus('reconnecting');
      retryRef.current = setTimeout(connectWs, 3000);
    };
    ws.onerror = () => {
      if (!mountedRef.current) return;
      setWsStatus('error');
      ws.close();
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    fetchTransactions();
    connectWs();
    return () => {
      mountedRef.current = false;
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [fetchTransactions, connectWs]);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setSelected(null); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const displayTxns = transactions.length > 0 ? transactions : propTransactions;

  return (
    <>
      <div className="card flex flex-col h-full">
        <div className="card-header flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-200">Live Transaction Feed</h2>
            <WsStatusBadge status={wsStatus} />
          </div>
          <div className="flex items-center gap-3">
            {loading && <span className="text-[10px] text-slate-500 font-mono animate-pulse">LOADING...</span>}
            <span className="text-xs text-slate-500 font-mono">{displayTxns.length} txns</span>
          </div>
        </div>

        <div className="card-body flex-1 overflow-y-auto scrollbar-thin">
          {error ? (
            <ErrorState error={error} onRetry={fetchTransactions} />
          ) : loading && displayTxns.length === 0 ? (
            <LoadingState />
          ) : displayTxns.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="space-y-2">
              {displayTxns.map((tx, i) => (
                <TransactionRow
                  key={tx.id ?? tx.transaction_id ?? i}
                  transaction={tx}
                  onClick={() => setSelected(tx)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {selected && (
        <TransactionModal transaction={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}

// ── Transaction row ───────────────────────────────────────────────────────── //
function TransactionRow({ transaction, onClick }) {
  const isFraud   = transaction.is_fraud;
  const riskScore = transaction.risk_score || 0;
  const amount    = transaction.amount || 0;

  const riskColor = riskScore > 0.75 ? 'bg-red-500'
    : riskScore > 0.5               ? 'bg-amber-500'
    :                                  'bg-emerald-500';

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 p-2.5 rounded-lg transition-all duration-200 text-left group cursor-pointer
        ${isFraud
          ? 'bg-red-500/10 border border-red-500/20 hover:bg-red-500/20'
          : 'bg-slate-800/50 border border-transparent hover:bg-slate-700/60 hover:border-slate-600/40'
        }`}
    >
      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${riskColor} ${isFraud ? 'animate-pulse' : ''}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-medium truncate ${isFraud ? 'text-red-400' : 'text-slate-300'}`}>
            {transaction.transaction_id || 'N/A'}
          </span>
          {isFraud && <span className="badge-fraud text-[10px] px-1.5 py-0">FRAUD</span>}
          {riskScore > 0.5 && riskScore <= 0.75 && (
            <span className="badge-warning text-[10px] px-1.5 py-0">SUSPICIOUS</span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-slate-400">{transaction.transaction_type}</span>
          <span className="text-[10px] text-slate-600">•</span>
          <span className="text-xs text-slate-400">{transaction.location || 'Unknown'}</span>
        </div>
      </div>

      <div className="text-right flex-shrink-0">
        <p className={`text-xs font-mono font-semibold ${isFraud ? 'text-red-400' : 'text-slate-200'}`}>
          {fmtUGX(amount)}
        </p>
        <p className={`text-[10px] font-mono ${isFraud ? 'text-red-400' : 'text-slate-500'}`}>
          Risk: {(riskScore * 100).toFixed(0)}%
        </p>
      </div>

      <svg className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 flex-shrink-0 transition-colors"
        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

// ── Detail modal ──────────────────────────────────────────────────────────── //
function TransactionModal({ transaction: tx, onClose }) {
  const isFraud   = tx.is_fraud;
  const riskScore = tx.risk_score || 0;

  const riskColor = riskScore > 0.75 ? '#ef4444'
    : riskScore > 0.5               ? '#f59e0b'
    : riskScore > 0.25              ? '#eab308'
    :                                  '#10b981';

  const riskLabel = riskScore > 0.75 ? 'CRITICAL'
    : riskScore > 0.5               ? 'ELEVATED'
    : riskScore > 0.25              ? 'MODERATE'
    :                                  'LOW';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Accent bar */}
        <div className={`h-1 w-full ${isFraud ? 'bg-red-500' : 'bg-emerald-500'}`} />

        {/* Header */}
        <div className="flex items-start justify-between p-5 pb-3">
          <div>
            {isFraud && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-widest text-red-400 bg-red-500/15 px-2 py-0.5 rounded-full border border-red-500/30 mb-2">
                ⚠ FRAUD DETECTED
              </span>
            )}
            <h3 className="text-sm font-mono font-semibold text-slate-200">{tx.transaction_id}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{fmtTime(tx.timestamp || tx.processed_at)}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Transfer flow */}
        <div className="mx-5 mb-3 p-4 bg-slate-800/60 rounded-xl border border-slate-700/40">
          <div className="flex items-center gap-3">
            {/* Sender */}
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">From</p>
              <p className="text-sm font-mono font-semibold text-slate-200 truncate">{tx.sender_account || '—'}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{institutionName(tx.sender_account)}</p>
            </div>

            {/* Arrow + amount */}
            <div className="flex flex-col items-center gap-1 flex-shrink-0 px-1">
              <p className={`text-xs font-mono font-bold whitespace-nowrap ${isFraud ? 'text-red-400' : 'text-emerald-400'}`}>
                {fmtUGX(tx.amount || 0)}
              </p>
              <svg className={`w-8 h-4 ${isFraud ? 'text-red-400' : 'text-emerald-400'}`}
                viewBox="0 0 32 16" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2 8h28M24 2l6 6-6 6" />
              </svg>
              <p className="text-[10px] text-slate-600 font-mono uppercase">{tx.transaction_type}</p>
            </div>

            {/* Receiver */}
            <div className="flex-1 min-w-0 text-right">
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">To</p>
              <p className="text-sm font-mono font-semibold text-slate-200 truncate">{tx.receiver_account || '—'}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{institutionName(tx.receiver_account)}</p>
            </div>
          </div>
        </div>

        {/* Details grid */}
        <div className="mx-5 mb-3 grid grid-cols-2 gap-2">
          <DetailCell label="Location"   value={tx.location || '—'} />
          <DetailCell label="Device"     value={tx.device_id || '—'} mono />
          <DetailCell label="IP Address" value={tx.ip_address || '—'} mono />
          <DetailCell label="Model"      value={tx.model_version || 'isolation_forest_v1'} mono />
          <DetailCell label="Processed"  value={fmtTime(tx.processed_at)} />
          <DetailCell label="Record"     value={tx.id ? `#${tx.id}` : '—'} mono />
        </div>

        {/* Risk bar */}
        <div className="mx-5 mb-3 p-4 bg-slate-800/60 rounded-xl border border-slate-700/40">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">AI Risk Score</p>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold" style={{ color: riskColor }}>
                {(riskScore * 100).toFixed(1)}%
              </span>
              <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded"
                style={{ color: riskColor, background: `${riskColor}18`, border: `1px solid ${riskColor}30` }}>
                {riskLabel}
              </span>
            </div>
          </div>
          <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${riskScore * 100}%`, background: riskColor }} />
          </div>
          <div className="flex justify-between mt-1">
            {['LOW', 'MOD', 'ELEV', 'CRIT'].map(l => (
              <span key={l} className="text-[9px] text-slate-600 font-mono">{l}</span>
            ))}
          </div>
        </div>

        {/* Fraud reason */}
        {tx.fraud_reason && (
          <div className="mx-5 mb-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
            <p className="text-[10px] text-red-400 font-mono uppercase tracking-wider mb-1">Fraud Signal</p>
            <p className="text-xs text-red-300">{tx.fraud_reason}</p>
          </div>
        )}

        {/* Footer */}
        <div className="px-5 pb-5">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-xs font-medium transition-colors border border-slate-700/60"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────── //
const INSTITUTION_MAP = {
  STB: 'Stanbic Bank',        CEN: 'Centenary Bank',      DFC: 'DFCU Bank',
  ABS: 'Absa Bank',           SCB: 'Standard Chartered',  CTB: 'Citibank',
  EQB: 'Equity Bank',         DTB: 'DTB Uganda',          ECO: 'Ecobank',
  KCB: 'KCB Bank',            BOA: 'Bank of Africa',      BRB: 'Bank of Baroda',
  BOI: 'Bank of India',       CAI: 'Cairo International', EXI: 'Exim Bank',
  HFB: 'Housing Finance',     NCB: 'NCBA Bank',           IMB: 'I&M Bank',
  SLM: 'Salaam Bank',         TRO: 'Tropical Bank',       UBA: 'UBA Uganda',
  PLB: 'Pearl of Africa',     ABC: 'ABC Capital',         GTB: 'GT Bank',
  OPP: 'Opportunity Bank',    YKB: 'Yako Bank',           BRC: 'BRAC Uganda',
  FTB: 'Finance Trust',       PRB: 'Pride Bank',          FIN: 'FINCA MDI',
  PRM: 'PRIDE MDI',           UGA: 'UGAFODE MDI',         MTN: 'MTN MoMo',
  ATL: 'Airtel Money',
};

function institutionName(account) {
  if (!account) return '';
  const prefix = account.slice(0, 3).toUpperCase();
  return INSTITUTION_MAP[prefix] || prefix;
}

function DetailCell({ label, value, mono = false }) {
  return (
    <div className="bg-slate-800/40 rounded-lg p-2.5">
      <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">{label}</p>
      <p className={`text-xs text-slate-300 mt-0.5 truncate ${mono ? 'font-mono' : ''}`}>{value}</p>
    </div>
  );
}

function WsStatusBadge({ status }) {
  const cfg = {
    connecting:   { dot: 'bg-amber-400 animate-pulse',  label: 'CONNECTING'   },
    live:         { dot: 'bg-emerald-400 animate-pulse', label: 'STREAMING'    },
    reconnecting: { dot: 'bg-amber-400 animate-pulse',  label: 'RECONNECTING' },
    error:        { dot: 'bg-red-500',                  label: 'WS ERROR'     },
  };
  const { dot, label } = cfg[status] ?? cfg.connecting;
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      <span className="text-[10px] text-slate-500 font-mono">{label}</span>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-8 gap-3">
      <div className="w-6 h-6 border-2 border-slate-600 border-t-emerald-400 rounded-full animate-spin" />
      <p className="text-sm text-slate-500">Fetching transactions...</p>
    </div>
  );
}

function ErrorState({ error, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-8 gap-3">
      <svg className="w-10 h-10 text-red-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <div>
        <p className="text-sm text-red-400">Failed to load transactions</p>
        <p className="text-xs text-slate-600 mt-1 font-mono">{error}</p>
      </div>
      <button onClick={onRetry} className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 px-3 py-1.5 rounded-md transition-colors">
        Retry
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-8">
      <svg className="w-12 h-12 text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 4v16h18V4H3zm2 14V6h14v12H5zm4-6h6" />
      </svg>
      <p className="text-sm text-slate-500">Waiting for transactions...</p>
      <p className="text-xs text-slate-600 mt-1">Start the simulation to see live data</p>
    </div>
  );
}