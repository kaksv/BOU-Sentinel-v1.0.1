import React from 'react';

export default function LiveTransactionFeed({ transactions = [] }) {
  return (
    <div className="card flex flex-col h-full">
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-200">Live Transaction Feed</h2>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-slate-500 font-mono">STREAMING</span>
          </div>
        </div>
        <span className="text-xs text-slate-500 font-mono">{transactions.length} txns</span>
      </div>

      <div className="card-body flex-1 overflow-y-auto scrollbar-thin">
        {transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <svg className="w-12 h-12 text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 4v16h18V4H3zm2 14V6h14v12H5zm4-6h6" />
            </svg>
            <p className="text-sm text-slate-500">Waiting for transactions...</p>
            <p className="text-xs text-slate-600 mt-1">Run mock_generator.py to start</p>
          </div>
        ) : (
          <div className="space-y-2">
            {transactions.map((tx, i) => (
              <TransactionRow key={tx.id || i} transaction={tx} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TransactionRow({ transaction, index }) {
  const isFraud = transaction.is_fraud;
  const riskScore = transaction.risk_score || 0;
  const amount = transaction.amount || 0;

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
      {/* Risk indicator dot */}
      <div className={`w-1.5 h-1.5 rounded-full ${riskColor} ${
        isFraud ? 'animate-pulse-fraud' : ''
      }`} />

      {/* Transaction info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono font-medium truncate ${
            isFraud ? 'text-fraud-400' : 'text-slate-300'
          }`}>
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

      {/* Amount & risk score */}
      <div className="text-right">
        <p className={`text-xs font-mono font-semibold ${
          isFraud ? 'text-fraud-400' : 'text-slate-200'
        }`}>
          {formattedAmount}
        </p>
        <p className={`text-[10px] font-mono ${
          isFraud ? 'text-fraud-400' : 'text-slate-500'
        }`}>
          Risk: {(riskScore * 100).toFixed(0)}%
        </p>
      </div>
    </div>
  );
}