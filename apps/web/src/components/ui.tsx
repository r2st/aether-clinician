import type { ReactNode } from 'react';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Button({
  children,
  className = '',
  variant = 'primary',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger';
}) {
  const styles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-slate-100 text-slate-800 hover:bg-slate-200',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }[variant];
  return (
    <button
      className={`rounded-md px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-red-100 text-red-800',
};

export function ConfidenceBadge({ band, value }: { band: string; value: number }) {
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
        CONFIDENCE_STYLES[band] ?? 'bg-slate-100 text-slate-700'
      }`}
    >
      {(value * 100).toFixed(0)}%
    </span>
  );
}

const SEVERITY_STYLES: Record<string, string> = {
  hard_block: 'border-red-700 bg-red-50 text-red-900',
  critical: 'border-red-500 bg-red-50 text-red-800',
  warning: 'border-amber-500 bg-amber-50 text-amber-900',
  info: 'border-blue-500 bg-blue-50 text-blue-900',
};

export function SafetyFlagCard({
  severity,
  isHardBlock,
  summary,
}: {
  severity: string;
  isHardBlock: boolean;
  summary: string;
}) {
  return (
    <div className={`rounded-md border-l-4 p-3 text-sm ${SEVERITY_STYLES[severity] ?? ''}`}>
      <span className="mr-2 font-semibold uppercase tracking-wide">
        {isHardBlock ? 'HARD BLOCK' : severity}
      </span>
      {summary}
    </div>
  );
}
