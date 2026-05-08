import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { SeverityBadge } from './SeverityBadge';
import { MapPin, Clock, Ambulance, Building2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function IncidentFeed() {
  const { incidents, selectedIncidentId, setSelectedIncident } = useStore();

  const sorted = [...incidents]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 20);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-sos-border flex-shrink-0">
        <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest">
          Live Incident Feed
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-sos-red animate-pulse" />
          <span className="text-[10px] text-sos-red font-mono">LIVE</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <AnimatePresence initial={false}>
          {sorted.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-sos-text-muted text-xs">
              No incidents detected
            </div>
          ) : (
            sorted.map((incident) => (
              <motion.div
                key={incident.id}
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 20, opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => setSelectedIncident(
                  selectedIncidentId === incident.id ? null : incident.id
                )}
                className={`
                  px-3 py-2.5 border-b border-sos-border cursor-pointer transition-all duration-150
                  ${selectedIncidentId === incident.id
                    ? 'bg-sos-cyan/5 border-l-2 border-l-sos-cyan'
                    : 'hover:bg-sos-card/50'
                  }
                  ${incident.severity === 'CRITICAL' ? 'border-l-2 border-l-sos-red' : ''}
                `}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <SeverityBadge severity={incident.severity} />
                      <span className="text-[10px] font-mono text-sos-text-dim truncate">
                        {incident.incident_number}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 text-[11px] text-sos-text-dim">
                      <MapPin className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{incident.address}</span>
                    </div>

                    <div className="flex items-center gap-3 mt-1">
                      {incident.ambulance_eta_minutes && (
                        <div className="flex items-center gap-1 text-[10px] text-sos-cyan">
                          <Ambulance className="w-3 h-3" />
                          <span>{incident.ambulance_eta_minutes.toFixed(0)}m ETA</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1 text-[10px] text-sos-text-muted">
                        <Clock className="w-3 h-3" />
                        <span>{formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <StatusDot status={incident.status} />
                    <span className="text-[9px] font-mono text-sos-text-muted">
                      {incident.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Timeline preview */}
                {selectedIncidentId === incident.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="mt-2 pt-2 border-t border-sos-border"
                  >
                    <div className="text-[10px] text-sos-text-dim font-mono mb-1">TIMELINE</div>
                    {Object.entries(incident.timeline || {}).map(([key, time]) => (
                      <div key={key} className="flex items-center gap-2 text-[10px] mb-0.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-sos-cyan flex-shrink-0" />
                        <span className="text-sos-text-dim capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="text-sos-text-muted ml-auto font-mono">
                          {new Date(time).toLocaleTimeString('en-IN', { hour12: false })}
                        </span>
                      </div>
                    ))}
                    <div className="mt-1.5 text-[10px] text-sos-text-dim">
                      Score: <span className="text-sos-amber font-mono">
                        {(incident.crash_probability_score * 100).toFixed(0)}%
                      </span>
                      {' · '}
                      Confidence: <span className="text-sos-cyan font-mono">{incident.confidence_level}</span>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    DETECTED: 'bg-sos-amber animate-pulse',
    CONFIRMED: 'bg-sos-red animate-pulse',
    DISPATCHED: 'bg-sos-cyan',
    EN_ROUTE: 'bg-sos-cyan animate-pulse',
    ON_SCENE: 'bg-sos-purple',
    TRANSPORTING: 'bg-sos-purple animate-pulse',
    RESOLVED: 'bg-sos-green',
    FALSE_ALARM: 'bg-sos-text-muted',
  };

  return (
    <div className={`w-2 h-2 rounded-full ${colors[status] || 'bg-sos-text-muted'}`} />
  );
}
