import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color: 'red' | 'cyan' | 'amber' | 'green' | 'purple';
  trend?: 'up' | 'down' | 'stable';
  animate?: boolean;
}

const colorMap = {
  red: {
    icon: 'text-sos-red',
    bg: 'bg-sos-red/10',
    border: 'border-sos-red/20',
    value: 'text-sos-red',
    glow: 'shadow-glow-red',
  },
  cyan: {
    icon: 'text-sos-cyan',
    bg: 'bg-sos-cyan/10',
    border: 'border-sos-cyan/20',
    value: 'text-sos-cyan',
    glow: 'shadow-glow-cyan',
  },
  amber: {
    icon: 'text-sos-amber',
    bg: 'bg-sos-amber/10',
    border: 'border-sos-amber/20',
    value: 'text-sos-amber',
    glow: 'shadow-glow-amber',
  },
  green: {
    icon: 'text-sos-green',
    bg: 'bg-sos-green/10',
    border: 'border-sos-green/20',
    value: 'text-sos-green',
    glow: 'shadow-glow-green',
  },
  purple: {
    icon: 'text-sos-purple',
    bg: 'bg-sos-purple/10',
    border: 'border-sos-purple/20',
    value: 'text-sos-purple',
    glow: '',
  },
};

export function StatCard({ title, value, subtitle, icon: Icon, color, animate = false }: Props) {
  const c = colorMap[color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-sos-card border ${c.border} rounded-lg p-3 shadow-card`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="text-[10px] text-sos-text-dim uppercase tracking-widest font-mono mb-1">
            {title}
          </div>
          <motion.div
            key={String(value)}
            initial={animate ? { y: 8, opacity: 0 } : false}
            animate={{ y: 0, opacity: 1 }}
            className={`text-2xl font-bold font-mono ${c.value}`}
          >
            {value}
          </motion.div>
          {subtitle && (
            <div className="text-[10px] text-sos-text-muted mt-0.5">{subtitle}</div>
          )}
        </div>
        <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-4 h-4 ${c.icon}`} />
        </div>
      </div>
    </motion.div>
  );
}
