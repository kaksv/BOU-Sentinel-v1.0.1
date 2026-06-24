import React, { useState, useEffect, useMemo } from 'react';
import { fetchInstitutions, fetchAtRiskInstitutions, TIER_OPTIONS, STATUS_OPTIONS } from './institutionApi';

const STATUS_BADGE = {
  compliant: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  warning: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  under_review: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  non_compliant: 'text-fraud-400 bg-fraud-500/10 border-fraud-500/30',
  suspended: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
};

const TIER_BADGE = {
  tier_1: 'border-bou-500/30 text-bou-300 bg-bou-500/10',
  tier_2: 'border-purple-500/30 text-purple-300 bg-purple-500/10',
  tier_3: 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10',
  tier_4: 'border-amber-500/30 text-amber-300 bg-amber-500/10',
  forex_bureau: 'border-cyan-500/30 text-cyan-300 bg-cyan-500/10',
  money_remitter: 'border-pink-500/30 text-pink-300 bg-pink-500/10',
  payment_provider: 'border-violet-500/30 text-violet-300 bg-violet-500/10',
  credit_reference: 'border-slate-500/30 text-slate-300 bg-slate-500/10',
};

function RiskBadge({ score }) {
  const color = score >= 60 ? 'text-fraud-400 bg-fraud-500/10' : score >= 35 ? 'text-amber-400 bg-amber-500/10' : 'text-emerald-400 bg-emerald-500/10';
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${color}`}>
      {score.toFixed(1)}
    </span>
  );
}

export default function InstitutionList({ mode = 'all', limit = 50 }) {
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTier, setSelectedTier] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        let data;
        if (mode === 'at-risk') {
          data = await fetchAtRiskInstitutions(limit);
          setInstitutions(data.institutions || []);
        } else {
          data = await fetchInstitutions({
            tier: selectedTier || undefined,
            status: selectedStatus || undefined,
            search: search || undefined,
            skip: page * pageSize,
            limit: pageSize,
          });
          if (!cancelled) {
            setInstitutions(data.institutions || []);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [mode, selectedTier, selectedStatus, search, page, limit]);

  const filteredCount = useMemo(() => {
    if (mode !== 'all') return institutions.length;
    return institutions.length;
  }, [institutions, mode]);

  if (loading && institutions.length === 0) {
    return (
      <div className="card">
        <div className="card-body py-8 text-center text-slate-500 text-sm">Loading institutions...</div>
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

  return (
    <div className="space-y-4">
      {/* Filters */}
      {mode === 'all' && (
        <div className="card">
          <div className="card-body py-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[200px]">
                <input
                  type="text"
                  placeholder="Search institution name or code..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-bou-500"
                />
              </div>
              <select
                value={selectedTier}
                onChange={(e) => { setSelectedTier(e.target.value); setPage(0); }}
                className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-bou-500"
              >
                <option value="">All Tiers</option>
                {TIER_OPTIONS.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <select
                value={selectedStatus}
                onChange={(e) => { setSelectedStatus(e.target.value); setPage(0); }}
                className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-bou-500"
              >
                <option value="">All Statuses</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            {mode === 'at-risk' ? 'At-Risk Institutions' : 'Regulated Institutions'}
          </h3>
          <span className="text-[10px] text-slate-500 font-mono">{filteredCount} results</span>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="px-4 py-2.5 font-medium">Code</th>
                  <th className="px-4 py-2.5 font-medium">Institution</th>
                  <th className="px-4 py-2.5 font-medium">Tier</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium text-right">Risk Score</th>
                  <th className="px-4 py-2.5 font-medium text-right">Compliance</th>
                  <th className="px-4 py-2.5 font-medium">Region</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {institutions.map((inst) => (
                  <tr key={inst.institution_code} className="hover:bg-slate-800/30 transition-colors cursor-pointer" onClick={() => onSelect && onSelect(inst.institution_code)}>
                    <td className="px-4 py-2.5 font-mono text-bou-300">{inst.institution_code}</td>
                    <td className="px-4 py-2.5 text-slate-200 font-medium">{inst.institution_name}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${TIER_BADGE[inst.tier] || 'border-slate-600 text-slate-400 bg-slate-800'}`}>
                        {inst.tier?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${STATUS_BADGE[inst.compliance_status] || 'border-slate-600 text-slate-400'}`}>
                        {inst.compliance_status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right"><RiskBadge score={inst.overall_risk_score} /></td>
                    <td className="px-4 py-2.5 text-right font-mono text-slate-300">{inst.compliance_score?.toFixed(1)}</td>
                    <td className="px-4 py-2.5 text-slate-400">{inst.region || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {institutions.length === 0 && (
            <div className="py-8 text-center text-slate-500 text-xs">No institutions found. Seed the database first.</div>
          )}
        </div>
      </div>
    </div>
  );
}