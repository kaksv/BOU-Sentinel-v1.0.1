import React, { useState, useEffect } from 'react';
import { fetchInstitutionDetails, refreshInstitutionMetrics, STATUS_OPTIONS } from './institutionApi';

const STATUS_COLORS = {
  compliant: { dot: 'bg-emerald-400', text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
  warning: { dot: 'bg-amber-400', text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  under_review: { dot: 'bg-blue-400', text: 'text-blue-400', border: 'border-blue-500/30', bg: 'bg-blue-500/10' },
  non_compliant: { dot: 'bg-fraud-400', text: 'text-fraud-400', border: 'border-fraud-500/30', bg: 'bg-fraud-500/10' },
  suspended: { dot: 'bg-slate-400', text: 'text-slate-400', border: 'border-slate-500/30', bg: 'bg-slate-500/10' },
};

function Pill({ children, className = '' }) {
  return <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${className}`}>{children}</span>;
}

function ProgressBar({ value, max = 100, color = 'bg-bou-500' }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function InstitutionDashboard({ institutionCode }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!institutionCode) return;
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const res = await fetchInstitutionDetails(institutionCode);
        if (!cancelled) setData(res);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [institutionCode]);

  const handleRefresh = async () => {
    if (!institutionCode || refreshing) return;
    try {
      setRefreshing(true);
      const res = await refreshInstitutionMetrics(institutionCode);
      setData(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshing(false);
    }
  };

  if (!institutionCode) {
    return (
      <div className="card h-full">
        <div className="card-body h-full flex items-center justify-center text-slate-600 text-sm">
          Select an institution from the list to view its full compliance profile.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card h-full">
        <div className="card-body h-full flex items-center justify-center text-slate-500 text-sm">Loading institution profile...</div>
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

  if (!data) return null;

  const theme = STATUS_COLORS[data.compliance_status] || STATUS_COLORS.compliant;
  const riskFlags = Array.isArray(data.risk_flags) ? data.risk_flags : [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card border-l-4" style={{ borderLeftColor: data.compliance_status === 'non_compliant' ? '#ef4444' : data.compliance_status === 'warning' ? '#f59e0b' : '#4c6ef5' }}>
        <div className="card-body">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-base font-semibold text-slate-100">{data.institution_name}</h3>
                <Pill className={`${theme.bg} ${theme.text} ${theme.border}`}>{data.compliance_status.replace('_', ' ')}</Pill>
              </div>
              <div className="text-[10px] text-slate-500 font-mono">{data.institution_code} • {data.license_number || 'No license'}</div>
              <div className="text-[10px] text-slate-600 font-mono mt-0.5">{data.registered_address || ''} {data.region || ''}</div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              {refreshing ? 'Refreshing...' : 'Refresh Metrics'}
            </button>
          </div>
        </div>
      </div>

      {/* Score Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="card">
          <div className="card-body py-3">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Risk Score</div>
            <div className={`text-xl font-semibold ${data.overall_risk_score >= 60 ? 'text-fraud-400' : data.overall_risk_score >= 35 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {data.overall_risk_score?.toFixed(1)}<span className="text-xs text-slate-600">/100</span>
            </div>
            <ProgressBar value={data.overall_risk_score} color={data.overall_risk_score >= 60 ? 'bg-fraud-500' : data.overall_risk_score >= 35 ? 'bg-amber-500' : 'bg-emerald-500'} />
          </div>
        </div>
        <div className="card">
          <div className="card-body py-3">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Compliance</div>
            <div className="text-xl font-semibold text-bou-300">{data.compliance_score?.toFixed(1)}<span className="text-xs text-slate-600">/100</span></div>
            <ProgressBar value={data.compliance_score} color="bg-bou-500" />
          </div>
        </div>
        <div className="card">
          <div className="card-body py-3">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">AML/CFT Score</div>
            <div className={`text-xl font-semibold ${data.fatf_compliance_score >= 65 ? 'text-emerald-400' : data.fatf_compliance_score >= 50 ? 'text-amber-400' : 'text-fraud-400'}`}>
              {data.fatf_compliance_score?.toFixed(1)}<span className="text-xs text-slate-600">/100</span></div>
            <ProgressBar value={data.fatf_compliance_score} color={data.fatf_compliance_score >= 65 ? 'bg-emerald-500' : data.fatf_compliance_score >= 50 ? 'bg-amber-500' : 'bg-fraud-500'} />
          </div>
        </div>
        <div className="card">
          <div className="card-body py-3">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1">Paid-Up Capital</div>
            <div className="text-xl font-semibold text-gold-400">{data.paid_up_capital?.toLocaleString()}</div>
            <div className="text-[10px] text-slate-600 font-mono mt-1">Ugx Millions</div>
          </div>
        </div>
      </div>

      {/* Risk Flags + Regulatory Thresholds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="card-header">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Active Risk Flags</h4>
          </div>
          <div className="card-body">
            {riskFlags.length === 0 ? (
              <div className="text-emerald-400 text-xs">No active risk flags.</div>
            ) : (
              <ul className="space-y-2">
                {riskFlags.map((flag, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-fraud-300">
                    <span className="mt-1 w-1 h-1 rounded-full bg-fraud-500 shrink-0" />
                    {flag}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Regulatory Thresholds (BOU)</h4>
          </div>
          <div className="card-body">
            {data.regulatory_thresholds ? (
              <div className="space-y-2 text-[11px] font-mono">
                <div className="flex justify-between"><span className="text-slate-500">Min. Capital (UGX Mn)</span><span className="text-slate-300">{data.regulatory_thresholds.min_capital_ugx_millions?.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Governing Law</span><span className="text-slate-300">{data.regulatory_thresholds.governing_law}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Tier</span><span className="text-bou-300">{data.regulatory_thresholds.name}</span></div>
              </div>
            ) : (
              <div className="text-slate-600 text-xs">No threshold data.</div>
            )}
          </div>
        </div>
      </div>

      {/* Compliance Checklist */}
      <div className="card">
        <div className="card-header">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Compliance Checklist</h4>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <CheckItem label="AML Policy Submitted" value={data.aml_policy_submitted} />
            <CheckItem label="AML Audit Current" value={data.aml_audit_report_current} />
            <CheckItem label="Quarterly Returns Current" value={data.quarterly_returns_current} />
            <CheckItem label="Currently Active" value={data.is_active} />
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckItem({ label, value }) {
  return (
    <div className={`flex items-center justify-between px-3 py-2 rounded-lg border ${value ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-fraud-500/20 bg-fraud-500/5'}`}>
      <span className="text-slate-400">{label}</span>
      <span className={`text-[10px] font-mono font-semibold ${value ? 'text-emerald-400' : 'text-fraud-400'}`}>
        {value ? 'PASS' : 'FAIL'}
      </span>
    </div>
  );
}