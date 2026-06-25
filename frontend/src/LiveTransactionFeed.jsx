import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL   = API_BASE.replace(/^http/, 'ws') + '/ws';
const MAX_FEED  = 100; // cap in-memory list

export default function LiveTransactionFeed({ transactions: propTransactions = [] }) {
  const [transactions, setTransactions] = useState([]);
  const [wsStatus, setWsStatus]         = useState('connecting'); // connecting | live | reconnecting | error
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const wsRef     = useRef(null);
  const retryRef  = useRef(null);
  const mountedRef = useRef(true);

  // ── Initial REST fetch ────────────────────────────────────────────────────
  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/transactions?limit=50`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (mountedRef.current) {
        // API returns newest-first; keep that order
        setTransactions(data.slice(0, MAX_FEED));
      }
    } catch (err) {
      if (mountedRef.current) setError(err.message);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  // ── WebSocket (live stream) ───────────────────────────────────────────────
  const connectWs = useCallback(() => {
    if (!mountedRef.current) return;
    setWsStatus('connecting');

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (mountedRef.current) setWsStatus('live');
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);
        // Only prepend actual transaction events, ignore compliance_alert / ws_stats
        if (msg.type === 'transaction' || (!msg.type && msg.transaction_id)) {
          setTransactions(prev => [msg, ...prev].slice(0, MAX_FEED));
        }
      } catch {
        // non-JSON pong / plain text — ignore
      }
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

  // ── Lifecycle ─────────────────────────────────────────────────────────────
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

  // Fall back to prop if fetch hasn't resolved yet
  const displayTxns = transactions.length > 0 ? transactions : propTransactions;

  return (
    <div className="card flex flex-col h-full">
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-200">Live Transaction Feed</h2>
          <WsStatusBadge status={wsStatus} />
        </div>
        <div className="flex items-center gap-3">
          {loading && (
            <span className="text-[10px] text-slate-500 font-mono animate-pulse">LOADING...</span>
          )}
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
              <TransactionRow key={tx.id ?? tx.transaction_id ?? i} transaction={tx} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function WsStatusBadge({ status }) {
  const cfg = {
    connecting:   { dot: 'bg-amber-400 animate-pulse',   label: 'CONNECTING' },
    live:         { dot: 'bg-emerald-400 animate-pulse',  label: 'STREAMING'  },
    reconnecting: { dot: 'bg-amber-400 animate-pulse',   label: 'RECONNECTING' },
    error:        { dot: 'bg-red-500',                   label: 'WS ERROR'   },
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
      <button
        onClick={onRetry}
        className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 hover:border-emerald-400/50 px-3 py-1.5 rounded-md transition-colors"
      >
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
      <p className="text-xs text-slate-600 mt-1">Run mock_generator.py to start</p>
    </div>
  );
}

function TransactionRow({ transaction }) {
  const isFraud   = transaction.is_fraud;
  const riskScore = transaction.risk_score || 0;
  const amount    = transaction.amount || 0;

  const riskColor = riskScore > 0.75
    ? 'bg-fraud-500'
    : riskScore > 0.5
    ? 'bg-amber-500'
    : 'bg-emerald-500';

  const formattedAmount = new Intl.NumberFormat('en-UG', {
    style: 'currency',
    currency: 'UGX',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

  return (
    <div className={`flex items-center gap-3 p-2.5 rounded-lg transition-all duration-300 animate-slide-up ${
      isFraud
        ? 'bg-fraud-500/10 border border-fraud-500/20'
        : 'bg-slate-800/50 border border-transparent hover:bg-slate-700/50'
    }`}>
      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${riskColor} ${isFraud ? 'animate-pulse-fraud' : ''}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-medium truncate ${isFraud ? 'text-fraud-400' : 'text-slate-300'}`}>
            {transaction.transaction_id || 'N/A'}
          </span>
          {isFraud && (
            <span className="badge-fraud text-[10px] px-1.5 py-0">FRAUD</span>
          )}
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
        <p className={`text-xs font-mono font-semibold ${isFraud ? 'text-fraud-400' : 'text-slate-200'}`}>
          {formattedAmount}
        </p>
        <p className={`text-[10px] font-mono ${isFraud ? 'text-fraud-400' : 'text-slate-500'}`}>
          Risk: {(riskScore * 100).toFixed(0)}%
        </p>
      </div>
    </div>
  );
}