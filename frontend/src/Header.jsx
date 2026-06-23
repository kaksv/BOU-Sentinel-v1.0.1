import React from 'react';

export default function Header({ wsConnected }) {
  return (
    <header className="border-b border-slate-700/50 bg-slate-800/50 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Left: Logo & Title */}
        <div className="flex items-center gap-4">
          {/* Logo mark */}
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-gold-400 to-amber-600 flex items-center justify-center shadow-lg shadow-gold-500/20">
            <svg className="w-6 h-6 text-slate-900" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>

          {/* Title & subtitle */}
          <div>
            <h1 className="text-xl font-bold text-gradient tracking-tight">
              BOU Sentinel
            </h1>
            <p className="text-xs text-slate-500 font-medium -mt-0.5">
              REAL-TIME FRAUD SURVEILLANCE SYSTEM
            </p>
          </div>
        </div>

        {/* Right: Connection status & timestamp */}
        <div className="flex items-center gap-6">
          {/* WebSocket status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-fraud-500'
            }`} />
            <span className="text-xs font-medium text-slate-400">
              {wsConnected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>

          {/* Clock */}
          <div className="text-right">
            <Clock />
          </div>

          {/* Bank of Uganda badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-700/50 border border-slate-600/50">
            <svg className="w-4 h-4 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
            </svg>
            <span className="text-xs font-medium text-slate-300">Bank of Uganda</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Clock() {
  const [time, setTime] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div>
      <p className="text-sm font-mono text-slate-300 font-medium">
        {time.toLocaleTimeString('en-UG', { hour12: false })}
      </p>
      <p className="text-[10px] text-slate-500">
        {time.toLocaleDateString('en-UG', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
      </p>
    </div>
  );
}