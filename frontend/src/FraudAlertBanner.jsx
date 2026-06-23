import React, { useState, useEffect } from 'react';

export default function FraudAlertBanner({ fraudCount = 0, recentFraud = false }) {
  const [show, setShow] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');

  useEffect(() => {
    if (recentFraud && fraudCount > 0) {
      setAlertMessage(`🚨 ${fraudCount} fraudulent transaction${fraudCount > 1 ? 's' : ''} detected in the last minute`);
      setShow(true);

      const timer = setTimeout(() => setShow(false), 8000);
      return () => clearTimeout(timer);
    }
  }, [fraudCount, recentFraud]);

  if (!show) return null;

  return (
    <div className="fixed top-20 right-6 z-50 max-w-sm animate-slide-up">
      <div className="bg-fraud-900/90 backdrop-blur-md border border-fraud-500/50 rounded-xl shadow-2xl shadow-fraud-500/20 p-4">
        <div className="flex items-start gap-3">
          {/* Siren icon */}
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-fraud-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-fraud-400 animate-siren" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-fraud-300">Fraud Alert</p>
            <p className="text-xs text-slate-300 mt-0.5">{alertMessage}</p>
          </div>

          {/* Close button */}
          <button
            onClick={() => setShow(false)}
            className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-700/50 hover:bg-slate-600/50 flex items-center justify-center transition-colors"
          >
            <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}