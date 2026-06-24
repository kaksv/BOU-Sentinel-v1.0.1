import React, { useState, useEffect, useMemo } from 'react';
import {
  fetchInstitutions,
  fetchAtRiskInstitutions,
  TIER_OPTIONS,
  STATUS_OPTIONS,
} from './institutionApi';

const PAGE_SIZE = 5;

export default function InstitutionList({
  mode = 'all',
  limit = 50,
  onSelect = null,
}) {
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingNext, setLoadingNext] = useState(false);
  const [error, setError] = useState(null);

  const [selectedTier, setSelectedTier] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [search, setSearch] = useState('');

  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  /**
   * Reset pagination when filters change
   */
  useEffect(() => {
    setInstitutions([]);
    setOffset(0);
    setHasMore(true);
  }, [selectedTier, selectedStatus, search]);

  /**
   * Fetch data (both initial + next pages)
   */
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        if (offset === 0) setLoading(true);
        else setLoadingNext(true);

        let data;

        if (mode === 'at-risk') {
          data = await fetchAtRiskInstitutions(limit);

          if (cancelled) return;

          setInstitutions(data.institutions || []);
          setHasMore(false);
        } else {
          data = await fetchInstitutions({
            tier: selectedTier || undefined,
            status: selectedStatus || undefined,
            search: search || undefined,
            skip: offset,
            limit: PAGE_SIZE,
          });

          if (cancelled) return;

          const newItems = data.institutions || [];

          setInstitutions(prev =>
            offset === 0 ? newItems : [...prev, ...newItems]
          );

          setHasMore(newItems.length === PAGE_SIZE);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setLoadingNext(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [offset, selectedTier, selectedStatus, search, mode, limit]);

  const filteredCount = useMemo(
    () => institutions.length,
    [institutions]
  );

  if (loading && institutions.length === 0) {
    return (
      <div className="card">
        <div className="card-body py-8 text-center text-slate-500 text-sm">
          Loading institutions...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card border border-fraud-500/30">
        <div className="card-body py-6 text-center text-fraud-400 text-sm">
          {error}
        </div>
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

              {/* Search */}
              <input
                type="text"
                value={search}
                placeholder="Search institution name or code..."
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs"
              />

              {/* Tier */}
              <select
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs"
              >
                <option value="">All Tiers</option>
                {TIER_OPTIONS.map(t => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>

              {/* Status */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs"
              >
                <option value="">All Statuses</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>

            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card">
        <div className="card-header flex justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            {mode === 'at-risk'
              ? 'At-Risk Institutions'
              : 'Regulated Institutions'}
          </h3>

          <span className="text-[10px] text-slate-500 font-mono">
            {filteredCount} results
          </span>
        </div>

        <div className="card-body p-0">
          <div className="overflow-x-auto">

            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="px-4 py-2.5">Code</th>
                  <th className="px-4 py-2.5">Institution</th>
                  <th className="px-4 py-2.5">Tier</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Risk Score</th>
                  <th className="px-4 py-2.5 text-right">Compliance</th>
                  <th className="px-4 py-2.5">Region</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-800/60">
                {institutions.map(inst => (
                  <tr
                    key={inst.institution_code}
                    className="hover:bg-slate-800/30 cursor-pointer"
                    onClick={() => onSelect?.(inst.institution_code)}
                  >
                    <td className="px-4 py-2.5 font-mono text-bou-300">
                      {inst.institution_code}
                    </td>
                    <td className="px-4 py-2.5 text-slate-200 font-medium">
                      {inst.institution_name}
                    </td>
                    <td className="px-4 py-2.5">{inst.tier}</td>
                    <td className="px-4 py-2.5">{inst.compliance_status}</td>
                    <td className="px-4 py-2.5 text-right">
                      {inst.overall_risk_score}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {inst.compliance_score?.toFixed(1)}
                    </td>
                    <td className="px-4 py-2.5">
                      {inst.region || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {institutions.length === 0 && (
              <div className="py-8 text-center text-slate-500 text-xs">
                No institutions found.
              </div>
            )}

          </div>

          {/* NEXT pagination */}
          {mode === 'all' && hasMore && (
            <div className="flex justify-center py-4">
              <button
                onClick={() => setOffset(prev => prev + PAGE_SIZE)}
                disabled={loadingNext}
                className="px-4 py-2 text-xs rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 disabled:opacity-50"
              >
                {loadingNext ? 'Loading...' : 'Next'}
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}