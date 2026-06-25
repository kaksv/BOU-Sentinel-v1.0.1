import React, { useEffect, useState } from 'react';
import { fetchInstitutions } from './institutionApi';

const PAGE_SIZE = 5;

export default function InstitutionList({ onSelect }) {
  /**
   * UI state (does NOT trigger API calls)
   */
  const [searchInput, setSearchInput] = useState('');

  const [tier, setTier] = useState('');
  const [status, setStatus] = useState('');

  /**
   * Query state (ONLY this triggers API calls)
   */
  const [query, setQuery] = useState({
    search: '',
    tier: '',
    status: '',
    page: 0,
  });

  /**
   * Data state
   */
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Fetch ONLY when query changes
   */
  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const res = await fetchInstitutions({
          search: query.search || undefined,
          tier: query.tier || undefined,
          status: query.status || undefined,
          skip: query.page * PAGE_SIZE,
          limit: PAGE_SIZE,
        });

        if (!alive) return;
        console.log('RAW ITEMS:', res);

        const items = res.institutions || [];

        setInstitutions(items);
        setHasMore(items.length === PAGE_SIZE);
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
  }, [query]);

  /**
   * Apply filters explicitly (NO auto refresh while typing)
   */
  const applyFilters = () => {
    setQuery({
      search: searchInput,
      tier,
      status,
      page: 0,
    });
  };

  /**
   * Pagination
   */
  const next = () => {
    if (hasMore) {
      setQuery(prev => ({ ...prev, page: prev.page + 1 }));
    }
  };

  const prev = () => {
    setQuery(prev => ({
      ...prev,
      page: Math.max(0, prev.page - 1),
    }));
  };

  /**
   * UI guards
   */
  if (error) {
    return (
      <div className="p-4 text-red-400 text-xs border border-red-500/30">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">

      {/* FILTER PANEL */}
      <div className="border border-slate-800 p-3 rounded space-y-2">

        {/* Search input */}
        <input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search institution name or code"
          className="w-full bg-slate-900 border border-slate-700 p-2 text-xs rounded"
        />

        {/* Filters */}
        <div className="flex gap-2">

          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs p-2 rounded"
          >
            <option value="">All Tiers</option>
            <option value="Tier I">Tier I</option>
            <option value="Tier II">Tier II</option>
            <option value="Tier III">Tier III</option>
            <option value="Non-Bank">Non-Bank</option>
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs p-2 rounded"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="revoked">Revoked</option>
            <option value="under_review">Under Review</option>
          </select>

          <button
            onClick={applyFilters}
            className="px-3 py-2 text-xs border border-slate-700 rounded bg-slate-800 hover:bg-slate-700"
          >
            Apply
          </button>

        </div>
      </div>

      {/* TABLE */}
      <div className="border border-slate-800 rounded overflow-hidden">

        <table className="w-full text-xs">
          <thead className="text-slate-500 border-b border-slate-800">
            <tr>
              <th className="p-2 text-left">Code</th>
              <th className="p-2 text-left">Name</th>
              <th className="p-2">Institution Type</th>
              <th className="p-2">Status</th>
              <th className="p-2 text-right">Risk</th>
              <th className="p-2 text-right">Head Quarter</th>
            </tr>
          </thead>

          <tbody>
            {institutions.map((inst) => (
              <tr
                key={inst.institution_code}
                onClick={() => onSelect?.(inst.institution_code)}
                className="hover:bg-slate-800 cursor-pointer"
              >
                <td className="p-2 font-mono text-blue-400">
                  {inst.institution_code}
                </td>
                <td className="p-2 text-slate-200">
                  {inst.institution_name
}
                </td>
                <td className="p-2">{inst.institution_type}</td>
                <td className="p-2">{inst.license_status}</td>
                <td className="p-2 text-right">
                  {inst.risk_score}
                </td>
                <td className="p-2 text-right">
                  {inst.headquarters}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {institutions.length === 0 && !loading && (
          <div className="p-4 text-center text-slate-500 text-xs">
            No institutions found
          </div>
        )}

      </div>

      {/* PAGINATION */}
      <div className="flex justify-between items-center">

        <button
          onClick={prev}
          disabled={query.page === 0 || loading}
          className="px-3 py-1 text-xs border border-slate-700 rounded disabled:opacity-40"
        >
          Previous
        </button>

        <div className="text-[10px] text-slate-500">
          Page {query.page + 1}
        </div>

        <button
          onClick={next}
          disabled={!hasMore || loading}
          className="px-3 py-1 text-xs border border-slate-700 rounded disabled:opacity-40"
        >
          Next
        </button>

      </div>

      {loading && (
        <div className="text-xs text-slate-500">
          Loading...
        </div>
      )}

    </div>
  );
}