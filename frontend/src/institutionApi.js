const API_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

export async function fetchSectorSummary() {
  const res = await fetch(`${API_URL}/api/institutions/summary`);
  if (!res.ok) throw new Error('Failed to fetch sector summary');
  return res.json();
}

export async function fetchInstitutions({ tier, status, region, search, skip = 0, limit = 100 } = {}) {
  const params = new URLSearchParams();
  if (tier) params.set('tier', tier);
  if (status) params.set('status', status);
  if (region) params.set('region', region);
  if (search) params.set('search', search);
  params.set('skip', skip);
  params.set('limit', limit);

  const res = await fetch(`${API_URL}/api/institutions/?${params}`);
  if (!res.ok) throw new Error('Failed to fetch institutions');
  return res.json();
}

export async function fetchAtRiskInstitutions(limit = 50) {
  const res = await fetch(`${API_URL}/api/institutions/at-risk?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch at-risk institutions');
  return res.json();
}

export async function fetchTierBreakdown() {
  const res = await fetch(`${API_URL}/api/institutions/tiers`);
  if (!res.ok) throw new Error('Failed to fetch tier breakdown');
  return res.json();
}

export async function fetchInstitutionDetails(code) {
  const res = await fetch(`${API_URL}/api/institutions/${encodeURIComponent(code)}`);
  if (!res.ok) throw new Error('Failed to fetch institution details');
  return res.json();
}

export async function seedInstitutions() {
  const res = await fetch(`${API_URL}/api/institutions/seed`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to seed institutions');
  return res.json();
}

export async function refreshInstitutionMetrics(code) {
  const res = await fetch(`${API_URL}/api/institutions/${encodeURIComponent(code)}/refresh`, { method: 'PUT' });
  if (!res.ok) throw new Error('Failed to refresh metrics');
  return res.json();
}

export const TIER_OPTIONS = [
  { value: 'tier_1', label: 'Tier I - Commercial Bank' },
  { value: 'tier_2', label: 'Tier II - Credit Institutions' },
  { value: 'tier_3', label: 'Tier III - Microfinance' },
  { value: 'tier_4', label: 'Tier IV - MDIs' },
  { value: 'forex_bureau', label: 'Forex Bureau' },
  { value: 'money_remitter', label: 'Money Remitter' },
  { value: 'payment_provider', label: 'Payment Provider' },
  { value: 'credit_reference', label: 'Credit Reference Bureau' },
];

export const STATUS_OPTIONS = [
  { value: 'compliant', label: 'Compliant', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  { value: 'warning', label: 'Warning', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  { value: 'under_review', label: 'Under Review', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  { value: 'non_compliant', label: 'Non-Compliant', color: 'text-fraud-400 bg-fraud-500/10 border-fraud-500/30' },
  { value: 'suspended', label: 'Suspended', color: 'text-slate-400 bg-slate-500/10 border-slate-500/30' },
];