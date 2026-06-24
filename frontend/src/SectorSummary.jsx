import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { fetchSectorSummary, fetchTierBreakdown, seedInstitutions } from './institutionApi';

const COLORS = {
  compliant: '#10b981',
  warning: '#f59e0b',
  under_review: '#3b82f6',
  non_compliant: '#ef4444',
  suspended: '#64748b',
};

export default function SectorSummary() {
  const [summary, setSummary] = useState(null);
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, t] = await Promise.all([
          fetchSectorSummary(),
          fetchTierBreakdown(),
        ]);
        if (!cancelled) {
          setSummary(s);
          setTiers(t.tiers || []);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="card">
        <div className="card-body py-8 text-center text-slate-500 text-sm">Loading sector summary...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card border border-fraud-500/30">
        <div className="card-body py-6 text-center text-fraud-400 text-sm">{error}</div>
      </div>
    );
  }

  const handleSeed = async () => {
    try {
      setSeeding(true);
      setSeedMsg(null);
      const res = await seedInstitutions();
      setSeedMsg(res.message || `Seeded ${res.total} institutions`);
      // Reload summary after seeding
      const [s, t] = await Promise.all([fetchSectorSummary(), fetchTierBreakdown()]);
      setSummary(s);
      setTiers(t.tiers || []);
    } catch (e) {
      setSeedMsg(e.message);
    } finally {
      setSeeding(false);
    }
  };

  if (!summary) return null;

  const pieData = [
    { name: 'Compliant', value: summary.compliant_count, color: COLORS.compliant },
    { name: 'Warning', value: summary.warning_count, color: COLORS.warning },
    { name: 'Under Review', value: summary.under_review_count, color: COLORS.under_review },
    { name: 'Non-Compliant', value: summary.non_compliant_count, color: COLORS.non_compliant },
    { name: 'Suspended', value: summary.suspended_count, color: COLORS.suspended },
  ].filter((d) => d.value > 0);

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
    <div className="space-y-6">
      {/* Seed Button */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Sector Summary</h3>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="px-3 py-1.5 rounded-lg bg-bou-600 hover:bg-bou-500 disabled:opacity-50 text-white text-[10px] font-semibold transition-colors"
        >
          {seeding ? 'Seeding...' : 'Seed Database'}
        </button>
      </div>
      {seedMsg && (
        <div className={`text-[11px] font-mono ${seedMsg.includes('Failed') ? 'text-fraud-400' : 'text-emerald-400'}`}>{seedMsg}</div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <div className="card-body py-4">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Total Institutions</div>
            <div className="text-2xl font-semibold text-slate-100">{summary.total_institutions.toLocaleString()}</div>
            <div className="text-[10px] text-slate-500 font-mono mt-1">BOU-regulated entities</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body py-4">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Compliance Rate</div>
            <div className="text-2xl font-semibold text-emerald-400">{summary.compliance_rate_pct}%</div>
            <div className="text-[10px] text-slate-500 font-mono mt-1">{summary.compliant_count} fully compliant</div>
          </div>
        </div>
        <div className="card border border-amber-500/20">
          <div className="card-body py-4">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Non-Compliance Rate</div>
            <div className="text-2xl font-semibold text-fraud-400">{summary.non_compliance_rate_pct}%</div>
            <div className="text-[10px] text-slate-500 font-mono mt-1">{summary.non_compliant_count + summary.suspended_count} flagged</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body py-4">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Avg Risk Score</div>
            <div className="text-2xl font-semibold text-gold-400">{summary.average_risk_score}<span className="text-sm text-slate-500">/100</span></div>
            <div className="text-[10px] text-slate-500 font-mono mt-1">Sector-weighted average</div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance Breakdown Pie */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-sm font-semibold text-slate-200">Compliance Breakdown</h3>
          </div>
          <div className="card-body">
            {pieData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-slate-500 text-xs">No data</div>
            ) : (
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={40}
                      paddingAngle={2}
                      stroke="none"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                      itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* Tier Breakdown Bar */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-sm font-semibold text-slate-200">Compliance by Regulatory Tier</h3>
          </div>
          <div className="card-body">
            {tiers.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-slate-500 text-xs">No data</div>
            ) : (
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={tiers} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                    <YAxis
                      dataKey="tier_name"
                      type="category"
                      width={140}
                      tick={{ fill: '#94a3b8', fontSize: 10 }}
                      axisLine={{ stroke: '#334155' }}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="compliance_rate_pct" name="Compliance %" radius={[3, 3, 3, 3]} barSize={14}>
                      {tiers.map((entry) => (
                        <Cell key={entry.tier} fill={entry.compliance_rate_pct >= 80 ? '#10b981' : entry.compliance_rate_pct >= 50 ? '#f59e0b' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}