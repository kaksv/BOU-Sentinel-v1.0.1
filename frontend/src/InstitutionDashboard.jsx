import React, { useEffect, useState } from 'react';
import {
  fetchInstitutionDetails,
  refreshInstitutionMetrics,
} from './institutionApi';

function Section({ title, children }) {
  return (
    <div className="border border-slate-800 rounded-lg">
      <div className="px-4 py-2 border-b border-slate-800">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {title}
        </h3>
      </div>
      <div className="p-4 space-y-2">{children}</div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between text-xs py-1">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-200 font-mono">{value ?? '-'}</span>
    </div>
  );
}

function Badge({ children, tone = 'slate' }) {
  const tones = {
    green: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
    amber: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
    red: 'border-red-500/30 text-red-400 bg-red-500/10',
    blue: 'border-blue-500/30 text-blue-400 bg-blue-500/10',
    slate: 'border-slate-700 text-slate-300 bg-slate-800/40',
  };

  return (
    <span className={`px-2 py-0.5 border rounded text-[11px] ${tones[tone]}`}>
      {children}
    </span>
  );
}

function Progress({ value }) {
  const pct = Math.min(100, Math.max(0, value || 0));

  return (
    <div className="w-full h-2 bg-slate-800 rounded">
      <div
        className="h-2 bg-blue-500 rounded transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function InstitutionDashboard({
  institutionCode,
  onClose,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!institutionCode) return;

    let alive = true;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const res = await fetchInstitutionDetails(institutionCode);

        if (alive) setData(res);
      } catch (e) {
        if (alive) setError(e.message);
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [institutionCode]);

  async function handleRefresh() {
    try {
      setRefreshing(true);
      const res = await refreshInstitutionMetrics(institutionCode);
      setData(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshing(false);
    }
  }

  if (!institutionCode) return null;

  if (loading) {
    return (
      <div className="p-6 text-slate-500 text-sm">
        Loading institution data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-red-400 text-sm">
        {error}
        <button
          onClick={() => window.location.reload()}
          className="ml-3 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const riskColor =
    data.risk_level === 'critical'
      ? 'red'
      : data.risk_level === 'high'
      ? 'red'
      : data.risk_level === 'medium'
      ? 'amber'
      : 'green';

  const issues = Array.isArray(data.compliance_issues)
    ? data.compliance_issues
    : [];

  return (
    <div className="space-y-4">

      {/* HEADER */}
      <div className="border border-slate-800 rounded-lg p-4">
        <div className="flex justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">
              {data.name}
            </h2>

            <div className="text-xs text-slate-500">
              {data.institution_code} • {data.tier} • {data.institution_type}
            </div>

            <div className="mt-2 flex gap-2">
              <Badge tone={riskColor}>
                Risk: {data.risk_level}
              </Badge>

              <Badge>
                License: {data.license_status}
              </Badge>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-3 py-1.5 text-xs border border-slate-700 rounded bg-slate-900"
            >
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>

            {onClose && (
              <button
                onClick={onClose}
                className="px-3 py-1.5 text-xs border border-slate-700 rounded"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>

      {/* RISK + AML GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        <Section title="Risk Engine">
          <Row label="Risk Score" value={`${data.risk_score}%`} />
          <Progress value={data.risk_score} />
          <Row label="Last Updated" value={data.last_risk_updated} />
        </Section>

        <Section title="AML / CFT">
          <Row label="Status" value={data.aml_compliance_status} />
          <Row label="Suspicious Transactions" value={data.suspicious_tx_count} />
          <Row label="Last Report" value={data.aml_last_report_date} />
        </Section>
      </div>

      {/* CAPITAL + LIQUIDITY */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        <Section title="Capital Adequacy">
          <Row label="Paid-up Capital (Bn UGX)" value={data.paid_up_capital_ugx_bn} />
          <Row label="Required Capital (Bn UGX)" value={data.minimum_capital_required_ugx_bn} />
          <Row label="Core Ratio (%)" value={data.core_capital_ratio} />
          <Row label="Total Ratio (%)" value={data.total_capital_ratio} />
        </Section>

        <Section title="Liquidity">
          <Row label="Liquidity Ratio (%)" value={data.liquidity_ratio} />
          <div className="pt-2">
            <Progress value={data.liquidity_ratio} />
          </div>
        </Section>
      </div>

      {/* GOVERNANCE */}
      <Section title="Corporate Governance">
        <div className="grid grid-cols-2 gap-2">
          <Row label="Independent Directors" value={data.independent_directors_count} />
          <Row label="Required Directors" value={data.minimum_directors_required} />
          <Row label="Internal Auditor" value={data.has_internal_auditor ? 'Yes' : 'No'} />
          <Row label="Company Secretary" value={data.has_company_secretary ? 'Yes' : 'No'} />
        </div>
      </Section>

      {/* TRANSACTIONS */}
      <Section title="Transaction Intelligence">
        <Row label="Total Transactions" value={data.total_transactions} />
        <Row label="Fraud Transactions" value={data.fraud_transactions} />
        <Row label="Fraud Rate (%)" value={data.fraud_rate} />
      </Section>

      {/* COMPLIANCE ISSUES */}
      <Section title="Compliance Issues">
        {issues.length === 0 ? (
          <div className="text-emerald-400 text-xs">
            No compliance issues detected
          </div>
        ) : (
          <ul className="space-y-1 text-xs text-red-400">
            {issues.map((issue, i) => (
              <li key={i}>• {issue}</li>
            ))}
          </ul>
        )}
      </Section>

      {/* FOOTER META */}
      <div className="text-[10px] text-slate-600 flex justify-between">
        <span>Created: {data.created_at}</span>
        <span>Updated: {data.updated_at}</span>
      </div>
    </div>
  );
}