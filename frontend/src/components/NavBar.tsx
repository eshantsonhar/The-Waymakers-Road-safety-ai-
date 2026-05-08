import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';
import { Shield, Radio, BarChart3, AlertTriangle } from 'lucide-react';

export function NavBar() {
  const { activeView, setActiveView, wsStatus, notifications, isDemoMode } = useStore();

  const unreadCount = notifications.filter((n) => !n.read).length;

  const navItems = [
    { id: 'command' as const, label: 'Command Center', icon: Radio, shortLabel: 'Command' },
    { id: 'citizen' as const, label: 'Citizen App', icon: Shield, shortLabel: 'Citizen' },
    { id: 'admin' as const, label: 'Analytics', icon: BarChart3, shortLabel: 'Analytics' },
  ];

  return (
    <div className="flex-shrink-0 h-14 bg-sos-surface border-b border-sos-border flex items-center px-4 gap-4 z-50">
      {/* Logo */}
      <div className="flex items-center gap-2 mr-4">
        <div className="w-8 h-8 rounded-lg bg-sos-red/20 border border-sos-red/40 flex items-center justify-center">
          <AlertTriangle className="w-4 h-4 text-sos-red" />
        </div>
        <div>
          <div className="text-sm font-bold text-sos-text text-glow-cyan tracking-wider">
            ROAD<span className="text-sos-red">SOS</span>
          </div>
          <div className="text-[9px] text-sos-text-dim tracking-widest uppercase">
            Emergency Intelligence
          </div>
        </div>
      </div>

      {/* Nav Items */}
      <div className="flex items-center gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200
                ${isActive
                  ? 'bg-sos-cyan/10 text-sos-cyan border border-sos-cyan/30'
                  : 'text-sos-text-dim hover:text-sos-text hover:bg-sos-card border border-transparent'
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{item.shortLabel}</span>
            </motion.button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Demo Mode Badge */}
      {isDemoMode && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-sos-amber/10 border border-sos-amber/30">
          <div className="w-1.5 h-1.5 rounded-full bg-sos-amber animate-pulse" />
          <span className="text-[10px] text-sos-amber font-mono font-medium tracking-wider">DEMO</span>
        </div>
      )}

      {/* Notification count */}
      {unreadCount > 0 && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-sos-red/10 border border-sos-red/30">
          <div className="w-1.5 h-1.5 rounded-full bg-sos-red animate-pulse" />
          <span className="text-[10px] text-sos-red font-mono font-medium">{unreadCount} ALERTS</span>
        </div>
      )}

      {/* WS Status */}
      <div className="flex items-center gap-1.5">
        <div className={`w-2 h-2 rounded-full ${
          wsStatus === 'connected' ? 'bg-sos-green shadow-glow-green' :
          wsStatus === 'connecting' ? 'bg-sos-amber animate-pulse' :
          'bg-sos-red'
        }`} />
        <span className="text-[10px] text-sos-text-dim font-mono hidden sm:inline">
          {wsStatus === 'connected' ? 'LIVE' : wsStatus === 'connecting' ? 'CONNECTING' : 'OFFLINE'}
        </span>
      </div>

      {/* Time */}
      <LiveClock />
    </div>
  );
}

function LiveClock() {
  const [time, setTime] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="text-[11px] font-mono text-sos-text-dim hidden md:block">
      {time.toLocaleTimeString('en-IN', { hour12: false })}
      <span className="text-sos-text-muted ml-1">IST</span>
    </div>
  );
}

import React from 'react';
