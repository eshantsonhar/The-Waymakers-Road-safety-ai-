import type { SeverityLevel } from '../types';

interface Props {
  severity: SeverityLevel;
  size?: 'sm' | 'md';
}

export function SeverityBadge({ severity, size = 'sm' }: Props) {
  const classes = {
    CRITICAL: 'bg-red-900/40 text-red-400 border-red-500/40',
    HIGH: 'bg-orange-900/40 text-orange-400 border-orange-500/40',
    MEDIUM: 'bg-amber-900/40 text-amber-400 border-amber-500/40',
    LOW: 'bg-green-900/40 text-green-400 border-green-500/40',
  };

  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-1';

  return (
    <span className={`inline-flex items-center rounded border font-mono font-semibold tracking-wider ${classes[severity]} ${sizeClasses}`}>
      {severity}
    </span>
  );
}
