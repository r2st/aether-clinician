import type { AutonomyTier, ProbabilityBand } from '@/lib/types';

const TIER: Record<AutonomyTier, { label: string; cls: string }> = {
  // Blue = informational, green = suggestive, amber = flag-for-review (architecture §8.2).
  informational: { label: 'Informational', cls: 'bg-blue-100 text-blue-800 border-blue-300' },
  suggestive: { label: 'Suggestive', cls: 'bg-green-100 text-green-800 border-green-300' },
  flag_for_review: {
    label: 'Flag for review',
    cls: 'bg-amber-100 text-amber-900 border-amber-400',
  },
};

export function AutonomyBadge({ tier }: { tier: AutonomyTier }) {
  const t = TIER[tier];
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${t.cls}`}>
      {t.label}
    </span>
  );
}

const BAND: Record<ProbabilityBand, string> = {
  high: 'bg-slate-800 text-white',
  moderate: 'bg-slate-600 text-white',
  low: 'bg-slate-300 text-slate-800',
  very_low: 'bg-slate-200 text-slate-600',
  insufficient_data: 'bg-slate-100 text-slate-500',
};

// Qualitative bands only — never numeric percentages (anti-automation-bias).
export function ProbabilityBandBadge({ band }: { band: ProbabilityBand }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${BAND[band]}`}>
      {band.replace('_', ' ').toUpperCase()}
    </span>
  );
}

export function CantMissBadge() {
  return (
    <span className="inline-flex animate-pulse items-center gap-1 rounded border border-orange-500 bg-orange-100 px-2 py-0.5 text-xs font-bold uppercase text-orange-900">
      ● Can&apos;t miss
    </span>
  );
}
