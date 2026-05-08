import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { WifiOff, Wifi } from 'lucide-react';

export function ConnectionStatus() {
  const { wsStatus } = useStore();

  return (
    <AnimatePresence>
      {wsStatus !== 'connected' && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className={`flex-shrink-0 flex items-center justify-center gap-2 py-1 text-xs font-mono ${
            wsStatus === 'connecting'
              ? 'bg-sos-amber/10 text-sos-amber border-b border-sos-amber/20'
              : 'bg-sos-red/10 text-sos-red border-b border-sos-red/20'
          }`}
        >
          {wsStatus === 'connecting' ? (
            <>
              <div className="w-1.5 h-1.5 rounded-full bg-sos-amber animate-pulse" />
              Connecting to RoadSoS backend...
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3" />
              Backend disconnected — running in demo mode. Reconnecting in 3s...
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
