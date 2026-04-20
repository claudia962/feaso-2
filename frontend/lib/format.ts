/** Currency / percent / integer formatters used across the dashboard. */

export const aud = (value: number | null | undefined, opts: { cents?: boolean } = {}) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: opts.cents ? 2 : 0,
  }).format(Number(value));
};

export const pct = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(decimals)}%`;
};

export const pctPoints = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(decimals)}%`;
};

export const integer = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-AU').format(Math.round(Number(value)));
};

export const recColor = (rec?: string | null): string => {
  switch (rec) {
    case 'strong_buy':   return 'bg-emerald-600';
    case 'buy':          return 'bg-emerald-500';
    case 'hold':         return 'bg-amber-500';
    case 'avoid':        return 'bg-orange-600';
    case 'strong_avoid': return 'bg-rose-700';
    default:             return 'bg-slate-400';
  }
};

export const recLabel = (rec?: string | null): string =>
  (rec || 'pending').replace('_', ' ').toUpperCase();
