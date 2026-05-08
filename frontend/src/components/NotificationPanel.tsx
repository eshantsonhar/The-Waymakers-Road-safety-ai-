import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { X, AlertTriangle, Ambulance, Building2, Info } from 'lucide-react';

export function NotificationPanel() {
  const { notifications, dismissNotification } = useStore();

  // Show only last 3 unread notifications
  const visible = notifications.filter((n) => !n.read).slice(0, 3);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {visible.map((notif) => (
          <motion.div
            key={notif.id}
            initial={{ x: 100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 100, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`
              pointer-events-auto w-80 rounded-lg border p-3 shadow-card
              ${notif.type === 'incident' || notif.type === 'alert'
                ? 'bg-sos-card border-sos-red/30 card-glow-red'
                : notif.type === 'ambulance'
                ? 'bg-sos-card border-sos-cyan/30 card-glow-cyan'
                : 'bg-sos-card border-sos-border'
              }
            `}
          >
            <div className="flex items-start gap-2">
              <div className={`mt-0.5 flex-shrink-0 ${
                notif.type === 'incident' || notif.type === 'alert' ? 'text-sos-red' :
                notif.type === 'ambulance' ? 'text-sos-cyan' : 'text-sos-text-dim'
              }`}>
                {notif.type === 'incident' || notif.type === 'alert' ? <AlertTriangle className="w-4 h-4" /> :
                 notif.type === 'ambulance' ? <Ambulance className="w-4 h-4" /> :
                 notif.type === 'hospital' ? <Building2 className="w-4 h-4" /> :
                 <Info className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-sos-text truncate">{notif.title}</div>
                <div className="text-[11px] text-sos-text-dim mt-0.5 line-clamp-2">{notif.message}</div>
                <div className="text-[10px] text-sos-text-muted mt-1 font-mono">
                  {new Date(notif.timestamp).toLocaleTimeString('en-IN', { hour12: false })}
                </div>
              </div>
              <button
                onClick={() => dismissNotification(notif.id)}
                className="flex-shrink-0 text-sos-text-muted hover:text-sos-text transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
