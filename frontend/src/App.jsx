import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import Header from './Header';
import StatCard from './StatCard';
import LiveTransactionFeed from './LiveTransactionFeed';
import RiskScoreGauge from './RiskScoreGauge';
import FraudHeatmap from './FraudHeatmap';
import FraudAlertBanner from './FraudAlertBanner';
import SectorSummary from './SectorSummary';
import InstitutionList from './InstitutionList';
import InstitutionDashboard from './InstitutionDashboard';
import Modal from './Modal';
import SimulationControl from './SimulationControl';

// In development, Vite proxy handles /api and /ws
// In production, set VITE_API_URL to your Render backend (e.g., https://bou-sentinel.onrender.com)
const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`;
const API_URL = BACKEND_URL;

// ================================================================
// Animated Number Counter
// ================================================================
function AnimatedNumber({ value, decimals = 0, suffix = '' }) {
  const [displayValue, setDisplayValue] = useState(0);
  const frameRef = useRef(null);
  const startValue = useRef(0);

  useEffect(() => {
    startValue.current = displayValue;
    const diff = value - startValue.current;
    const duration = 800; // ms
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = startValue.current + diff * eased;

      setDisplayValue(current);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [value]);

  return (
    <span>{displayValue.toFixed(decimals)}{suffix}</span>
  );
}

// ================================================================
// Connection Status Overlay
// ================================================================
function ConnectionStatus({ wsConnected, lastReconnect }) {
  const [showDisconnected, setShowDisconnected] = useState(false);

  useEffect(() => {
    if (!wsConnected) {
      setShowDisconnected(true);
    } else {
      const timer = setTimeout(() => setShowDisconnected(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [wsConnected, lastReconnect]);

  if (!showDisconnected) return null;

  return (
    <div className={`fixed bottom-6 left-6 z-50 flex items-center gap-2 px-3 py-2 rounded-lg backdrop-blur-md transition-all duration-500 ${
      wsConnected
        ? 'bg-emerald-900/60 border border-emerald-500/30'
        : 'bg-fraud-900/60 border border-fraud-500/30 animate-pulse'
    }`}>
      <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-fraud-400'}`} />
      <span className="text-xs font-medium text-slate-300">
        {wsConnected ? 'Connected to stream' : 'Reconnecting...'}
      </span>
    </div>
  );
}

// ================================================================
// Main App Component
// ================================================================
export default function App() {
  // State
  const [wsConnected, setWsConnected] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState({
    total_transactions: 0,
    fraud_transactions: 0,
    fraud_rate: 0,
    avg_risk_score: 0,
    recent_activity: [],
    ws_connected_clients: 0,
  });
  const [currentRiskScore, setCurrentRiskScore] = useState(0);
  const [recentFraudDetected, setRecentFraudDetected] = useState(false);
  const [recentFraudCount, setRecentFraudCount] = useState(0);
  const [reconnectVersion, setReconnectVersion] = useState(0);
  const [systemInfo, setSystemInfo] = useState({
    model_loaded: false,
    redis_connected: false,
    ws_clients: 0,
  });

  const [selectedInstitutionCode, setSelectedInstitutionCode] = useState(null);
  const [activeTab, setActiveTab] = useState('fraud'); // 'fraud' | 'sector'

  const wsRef = useRef(null);
  const fraudTimerRef = useRef(null);

  // Expose institution selector globally for table row clicks
  useEffect(() => {
    window.__institutionCode = (code) => {
      setSelectedInstitutionCode(code);
      setActiveTab('sector');
    };
    return () => { window.__institutionCode = null; };
  }, []);

  // ================================================================
  // WebSocket Connection
  // ================================================================
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('🔗 WebSocket connected');
        setWsConnected(true);
        setReconnectVersion(v => v + 1);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleIncomingTransaction(data);
        } catch (e) {
          // Could be a server status message
          console.debug('WebSocket message:', event.data);
        }
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setWsConnected(false);
        wsRef.current = null;
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setTimeout(connectWebSocket, 3000);
    }
  }, []);

  // ================================================================
  // Handle Incoming Transaction from WebSocket
  // ================================================================
  const handleIncomingTransaction = useCallback((data) => {
    setTransactions((prev) => {
      const updated = [data, ...prev].slice(0, 100);
      return updated;
    });

    if (data.risk_score !== undefined) {
      setCurrentRiskScore(prev => {
        // Weighted: 30% new, 70% previous for smooth gauge
        return prev * 0.7 + data.risk_score * 0.3;
      });
    }

    // Track recent fraud for alert
    if (data.is_fraud) {
      setRecentFraudDetected(true);
      setRecentFraudCount(prev => prev + 1);

      // Reset alert after 10 seconds of no fraud
      clearTimeout(fraudTimerRef.current);
      fraudTimerRef.current = setTimeout(() => {
        setRecentFraudDetected(false);
        setRecentFraudCount(0);
      }, 10000);
    }
  }, []);

  // ================================================================
  // Fetch Stats from API
  // ================================================================
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (e) {
      console.warn('Failed to fetch stats:', e);
    }
  }, []);

  const fetchSystemInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/status`);
      if (response.ok) {
        const data = await response.json();
        setSystemInfo({
          model_loaded: data.model_loaded,
          redis_connected: data.redis_connected,
          ws_clients: data.ws_clients || 0,
        });
      }
    } catch (e) {
      // Silently fail
    }
  }, []);

  // ================================================================
  // Effects
  // ================================================================
  useEffect(() => {
    connectWebSocket();
    fetchStats();
    fetchSystemInfo();

    const statsInterval = setInterval(fetchStats, 10000);
    const systemInterval = setInterval(fetchSystemInfo, 30000);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      clearInterval(statsInterval);
      clearInterval(systemInterval);
      clearTimeout(fraudTimerRef.current);
    };
  }, [connectWebSocket, fetchStats, fetchSystemInfo]);

  // ================================================================
  // Derived Values
  // ================================================================
  const {
    total_transactions: totalTxns = 0,
    fraud_transactions: fraudTxns = 0,
    fraud_rate: fraudRate = 0,
    avg_risk_score: avgRisk = 0,
    recent_activity: activityData = [],
  } = stats;

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Background pattern */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #94a3b8 1px, transparent 0)`,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Header */}
      <Header wsConnected={wsConnected} />

      {/* Fraud Alert Banner */}
      <FraudAlertBanner
        fraudCount={recentFraudCount}
        recentFraud={recentFraudDetected}
      />

      {/* Connection Status */}
      <ConnectionStatus
        wsConnected={wsConnected}
        lastReconnect={reconnectVersion}
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6 relative">
        {/* Tab Switcher */}
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => setActiveTab('fraud')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'fraud'
                ? 'bg-bou-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            🔍 Fraud Monitor
          </button>
          <button
            onClick={() => setActiveTab('sector')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'sector'
                ? 'bg-bou-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            🏛️ Sector Overview
          </button>
        </div>

        {/* Stats Row */}
        {activeTab === 'fraud' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              title="Total Transactions"
              value={<AnimatedNumber value={totalTxns} />}
              subtitle="All time monitored"
              trend={5}
              color="slate"
              icon={
                <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 4v16h18V4H3zm2 14V6h14v12H5zm4-6h6" />
                </svg>
              }
            />
            <StatCard
              title="Fraud Detected"
              value={<AnimatedNumber value={fraudTxns} />}
              subtitle={`${fraudRate.toFixed(2)}% of all transactions`}
              trend={fraudRate > 10 ? -8 : 12}
              color="red"
              isFraud={fraudRate > 5}
              icon={
                <svg className="w-5 h-5 text-fraud-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              }
            />
            <StatCard
              title="Fraud Rate"
              value={<AnimatedNumber value={fraudRate} decimals={2} suffix="%" />}
              subtitle="Percentage flagged"
              color="amber"
              icon={
                <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 4.5h18M3 9h18m-6 4.5h6M3 13.5h3m3 0h3" />
                </svg>
              }
            />
            <StatCard
              title="Avg Risk Score"
              value={<AnimatedNumber value={avgRisk * 100} decimals={1} suffix="%" />}
              subtitle="Model confidence"
              color="gold"
              icon={
                <svg className="w-5 h-5 text-gold-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              }
            />
            <SimulationControl />
          </div>

        )}
        {/* Fraud Monitor Tab */}
        {activeTab === 'fraud' && (
          <>
            {/* Middle Row: Transaction Volume Chart */}
            <div className="mb-6">
              <TransactionVolumeChart activityData={activityData} />
            </div>

            {/* System Status Bar */}
            <div className="mb-6">
              <SystemStatusBar info={systemInfo} wsConnected={wsConnected} />
            </div>

            {/* Bottom Row: 3-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1 h-[500px]">
                <LiveTransactionFeed transactions={transactions} />
              </div>
              <div className="lg:col-span-1">
                <RiskScoreGauge riskScore={currentRiskScore} transactionCount={totalTxns} />
              </div>
              <div className="lg:col-span-1">
                <FraudHeatmap activityData={activityData} />
              </div>
            </div>
          </>
        )}

        {/* Sector Overview Tab */}
        {activeTab === 'sector' && (
          <>
            <div className="space-y-6">
              <SectorSummary />

              <InstitutionList
                mode="all"
                onSelect={setSelectedInstitutionCode}
              />
            </div>

            <Modal
              open={!!selectedInstitutionCode}
              onClose={() => setSelectedInstitutionCode(null)}
            >
              <InstitutionDashboard
                institutionCode={selectedInstitutionCode}
                onClose={() => setSelectedInstitutionCode(null)}
              />
            </Modal>
          </>
        )}

        {/* Footer */}
        <footer className="mt-8 pb-6 border-t border-slate-800 pt-4 text-slate-600 font-mono mx -10">
          <div className="flex flex-row items-center sm:justify-between gap-4 text-[10px]   sm:flex-row">
            <span>BOU Sentinel v1.0.0 • Real-Time Fraud Detection & Regulatory Oversight</span>
            <span>Built for Bank of Uganda Hackathon</span>
          </div>
          <div className='mt-12 flex items-center justify-center  text-[10px] text-center mb-0 pb-0'> <span>&copy;{new Date().getFullYear()}. All rights reserved.</span></div>
        </footer>
      </main>
    </div>
  );
}

// ================================================================
// System Status Bar
// ================================================================
function SystemStatusBar({ info, wsConnected }) {
  const statusDot = (active) => (
    <div className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
  );

  return (
    <div className="card">
      <div className="card-body py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              {statusDot(wsConnected)}
              <span className="text-[10px] text-slate-500 font-mono">WEBSOCKET</span>
            </div>
            <div className="flex items-center gap-2">
              {statusDot(info.redis_connected)}
              <span className="text-[10px] text-slate-500 font-mono">REDIS</span>
            </div>
            <div className="flex items-center gap-2">
              {statusDot(info.model_loaded)}
              <span className="text-[10px] text-slate-500 font-mono">AI MODEL</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-600 font-mono">WS CLIENTS: {info.ws_clients}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-2 py-0.5 rounded bg-slate-700/50 border border-slate-600/50">
              <span className="text-[9px] font-mono text-slate-500">
                Isolation Forest v1
              </span>
            </div>
            <div className="px-2 py-0.5 rounded bg-slate-700/50 border border-slate-600/50">
              <span className="text-[9px] font-mono text-slate-500">
                <SimulationControl />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================================================================
// Transaction Volume vs Fraud Volume Chart
// ================================================================
function TransactionVolumeChart({ activityData }) {
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    if (activityData.length === 0) return;

    const formatted = activityData.slice().reverse().map((item) => {
      const minute = item.minute
        ? new Date(item.minute).toLocaleTimeString('en-UG', { hour: '2-digit', minute: '2-digit', hour12: false })
        : 'N/A';
      return {
        minute,
        total: item.total || 0,
        fraud: item.fraud || 0,
      };
    });

    setChartData(formatted);
  }, [activityData]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 shadow-xl">
          <p className="text-xs text-slate-300 font-medium mb-1">{label}</p>
          {payload.map((entry, idx) => (
            <p key={idx} className="text-xs font-mono" style={{ color: entry.color }}>
              {entry.name}: {entry.value.toLocaleString()}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Transaction Volume vs Fraud Volume</h2>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-bou-500" />
            <span className="text-[10px] text-slate-400 font-medium">Total</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm bg-fraud-500" />
            <span className="text-[10px] text-slate-400 font-medium">Fraud</span>
          </div>
        </div>
      </div>
      <div className="card-body">
        <div style={{ width: '100%', height: 250 }}>
          <ResponsiveContainer>
            <ComposedChart data={chartData.length > 0 ? chartData : [{ minute: 'No data', total: 0, fraud: 0 }]} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
              <XAxis
                dataKey="minute"
                tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={{ stroke: '#334155' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '10px', color: '#94a3b8' }} />
              <Bar dataKey="total" fill="#4c6ef5" radius={[2, 2, 0, 0]} barSize={16} opacity={0.7} name="Total Transactions" />
              <Line
                type="monotone"
                dataKey="fraud"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ r: 3, fill: '#ef4444', stroke: '#ef4444' }}
                activeDot={{ r: 5, stroke: '#ef4444', strokeWidth: 2 }}
                name="Fraud Detected"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}