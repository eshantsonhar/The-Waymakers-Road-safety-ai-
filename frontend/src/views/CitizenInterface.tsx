import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store/useStore';
import { useApi } from '../hooks/useApi';
import { SeverityBadge } from '../components/SeverityBadge';
import { MobileTelemetryDashboard } from '../mobile/MobileTelemetryDashboard';
import {
  AlertTriangle, Phone, MapPin, Clock, Wifi, WifiOff,
  Activity, Building2, Ambulance, CheckCircle, X, Zap, Smartphone
} from 'lucide-react';

type DetectionState = 'monitoring' | 'alert' | 'confirmed' | 'sos_active';

const CRASH_SCENARIOS = [
  { id: 'MINOR_COLLISION', label: 'Minor Collision', color: 'amber', icon: '🚗' },
  { id: 'MODERATE_CRASH', label: 'Moderate Crash', color: 'orange', icon: '💥' },
  { id: 'SEVERE_CRASH', label: 'Severe Crash', color: 'red', icon: '🚨' },
  { id: 'ROLLOVER', label: 'Rollover', color: 'red', icon: '🔄' },
];

const MOCK_HOSPITALS = [
  { name: 'Manipal Hospital Whitefield', distance: '3.2 km', eta: '8 min', score: 92, icu: 18, trauma: true },
  { name: 'Apollo Hospital Bannerghatta', distance: '5.1 km', eta: '12 min', score: 88, icu: 22, trauma: true },
  { name: 'Fortis Hospital', distance: '6.8 km', eta: '15 min', score: 81, icu: 15, trauma: true },
];

const MOCK_CONTACTS = [
  { name: 'Priya Sharma', relation: 'Spouse', phone: '+91 98765 43210' },
  { name: 'Rajesh Kumar', relation: 'Father', phone: '+91 87654 32109' },
  { name: 'Emergency Services', relation: 'Police', phone: '100' },
];

export function CitizenInterface() {
  const { isOfflineMode, toggleOfflineMode, addNotification } = useStore();
  const { triggerSOS, simulateCrash } = useApi();

  const [detectionState, setDetectionState] = useState<DetectionState>('monitoring');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [sosActive, setSosActive] = useState(false);
  const [ambulanceEta, setAmbulanceEta] = useState<number | null>(null);
  const [ambulanceDistance, setAmbulanceDistance] = useState<number | null>(null);
  const [notificationsSent, setNotificationsSent] = useState(false);
  const [simulationResult, setSimulationResult] = useState<{ scenario: string; probability: number; severity: string } | null>(null);
  const [sosCountdown, setSosCountdown] = useState<number | null>(null);

  // Elapsed timer when SOS is active
  useEffect(() => {
    if (!sosActive) return;
    const timer = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [sosActive]);

  // Simulate ambulance approaching
  useEffect(() => {
    if (!sosActive || ambulanceEta === null) return;
    if (ambulanceEta <= 0) return;
    const timer = setInterval(() => {
      setAmbulanceEta((eta) => Math.max(0, (eta ?? 0) - 1 / 60));
      setAmbulanceDistance((d) => Math.max(0, (d ?? 0) - 0.05));
    }, 1000);
    return () => clearInterval(timer);
  }, [sosActive, ambulanceEta]);

  const handleSOS = useCallback(async () => {
    if (sosActive) return;

    // 3-second countdown
    setSosCountdown(3);
    for (let i = 2; i >= 0; i--) {
      await new Promise((r) => setTimeout(r, 1000));
      setSosCountdown(i);
    }
    setSosCountdown(null);

    setSosActive(true);
    setDetectionState('sos_active');
    setElapsedSeconds(0);
    setAmbulanceEta(8.5);
    setAmbulanceDistance(4.2);

    addNotification({
      id: `sos-${Date.now()}`,
      type: 'alert',
      title: '🆘 SOS Triggered',
      message: 'Emergency services have been notified. Ambulance dispatched.',
      severity: 'HIGH',
      timestamp: new Date().toISOString(),
      read: false,
    });

    // Simulate notification sending
    setTimeout(() => setNotificationsSent(true), 2000);

    try {
      await triggerSOS(12.9716, 77.5946);
    } catch {
      // Continue in demo mode
    }
  }, [sosActive, addNotification, triggerSOS]);

  const handleCancelSOS = useCallback(() => {
    setSosActive(false);
    setDetectionState('monitoring');
    setElapsedSeconds(0);
    setAmbulanceEta(null);
    setAmbulanceDistance(null);
    setNotificationsSent(false);
  }, []);

  const handleSimulateCrash = useCallback(async (scenario: string) => {
    setDetectionState('alert');
    try {
      const result = await simulateCrash(scenario);
      const maxProb = result.max_probability || 0.85;
      const severity = maxProb >= 0.9 ? 'CRITICAL' : maxProb >= 0.75 ? 'HIGH' : 'MEDIUM';
      setSimulationResult({ scenario, probability: maxProb, severity });

      if (maxProb >= 0.75) {
        setDetectionState('confirmed');
        setTimeout(() => {
          if (!sosActive) {
            setSosActive(true);
            setDetectionState('sos_active');
            setAmbulanceEta(7.2);
            setAmbulanceDistance(3.8);
          }
        }, 2000);
      }
    } catch {
      setSimulationResult({ scenario, probability: 0.87, severity: 'HIGH' });
      setDetectionState('confirmed');
    }
  }, [simulateCrash, sosActive]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-full overflow-y-auto bg-sos-bg">
      <div className="max-w-md mx-auto px-4 py-4 pb-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-lg font-bold text-sos-text">RoadSoS</div>
            <div className="text-[11px] text-sos-text-dim">Citizen Emergency App</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleOfflineMode}
              className={`flex items-center gap-1.5 px-2 py-1 rounded border text-[10px] font-mono transition-all ${
                isOfflineMode
                  ? 'bg-sos-red/10 text-sos-red border-sos-red/30'
                  : 'bg-sos-green/10 text-sos-green border-sos-green/30'
              }`}
            >
              {isOfflineMode ? <WifiOff className="w-3 h-3" /> : <Wifi className="w-3 h-3" />}
              {isOfflineMode ? 'OFFLINE' : 'ONLINE'}
            </button>
          </div>
        </div>

        {/* Detection Status */}
        <motion.div
          className={`rounded-xl border p-4 mb-4 ${
            detectionState === 'sos_active' ? 'bg-sos-red/10 border-sos-red/40 card-glow-red' :
            detectionState === 'confirmed' ? 'bg-orange-900/20 border-orange-500/40' :
            detectionState === 'alert' ? 'bg-sos-amber/10 border-sos-amber/40' :
            'bg-sos-card border-sos-border'
          }`}
          animate={detectionState === 'sos_active' ? { boxShadow: ['0 0 0 0 rgba(255,45,85,0.3)', '0 0 20px 8px rgba(255,45,85,0)', '0 0 0 0 rgba(255,45,85,0.3)'] } : {}}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest">
              Crash Detection Status
            </div>
            <div className={`flex items-center gap-1.5 text-[10px] font-mono ${
              detectionState === 'sos_active' ? 'text-sos-red' :
              detectionState === 'confirmed' ? 'text-orange-400' :
              detectionState === 'alert' ? 'text-sos-amber' :
              'text-sos-green'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                detectionState === 'monitoring' ? 'bg-sos-green' :
                detectionState === 'alert' ? 'bg-sos-amber animate-pulse' :
                'bg-sos-red animate-pulse'
              }`} />
              {detectionState === 'monitoring' ? 'MONITORING' :
               detectionState === 'alert' ? 'ALERT' :
               detectionState === 'confirmed' ? 'CRASH CONFIRMED' :
               'SOS ACTIVE'}
            </div>
          </div>

          {detectionState === 'sos_active' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs text-sos-text-dim">Elapsed Time</div>
                <div className="text-lg font-mono font-bold text-sos-red">{formatTime(elapsedSeconds)}</div>
              </div>
              {ambulanceEta !== null && (
                <div className="flex items-center justify-between">
                  <div className="text-xs text-sos-text-dim flex items-center gap-1">
                    <Ambulance className="w-3 h-3 text-sos-cyan" /> Ambulance ETA
                  </div>
                  <div className="text-sm font-mono font-bold text-sos-cyan">
                    {ambulanceEta.toFixed(0)} min ({ambulanceDistance?.toFixed(1)} km)
                  </div>
                </div>
              )}
              {notificationsSent && (
                <div className="flex items-center gap-1.5 text-[11px] text-sos-green">
                  <CheckCircle className="w-3 h-3" />
                  Emergency contacts notified
                </div>
              )}
            </div>
          )}

          {detectionState === 'confirmed' && simulationResult && (
            <div className="mt-2">
              <div className="text-xs text-sos-text-dim">Crash Probability</div>
              <div className="text-2xl font-mono font-bold text-sos-red">
                {(simulationResult.probability * 100).toFixed(0)}%
              </div>
              <div className="text-[11px] text-sos-text-dim mt-1">
                Severity: <SeverityBadge severity={simulationResult.severity as 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'} />
              </div>
              <div className="text-[11px] text-sos-amber mt-1 animate-pulse">
                Auto-dispatching emergency services...
              </div>
            </div>
          )}

          {detectionState === 'monitoring' && (
            <div className="flex items-center gap-2 mt-1">
              <Activity className="w-4 h-4 text-sos-green" />
              <div className="text-xs text-sos-text-dim">Sensors active — monitoring for crash events</div>
            </div>
          )}
        </motion.div>

        {/* SOS Button */}
        <div className="flex justify-center mb-4">
          <AnimatePresence mode="wait">
            {sosCountdown !== null ? (
              <motion.div
                key="countdown"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="w-32 h-32 rounded-full bg-sos-red/20 border-4 border-sos-red flex items-center justify-center"
              >
                <span className="text-5xl font-bold font-mono text-sos-red">{sosCountdown}</span>
              </motion.div>
            ) : sosActive ? (
              <motion.button
                key="cancel"
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                onClick={handleCancelSOS}
                className="w-32 h-32 rounded-full bg-sos-surface border-4 border-sos-red/50 flex flex-col items-center justify-center gap-1 hover:bg-sos-red/10 transition-colors"
              >
                <X className="w-8 h-8 text-sos-red" />
                <span className="text-[10px] font-mono text-sos-red">CANCEL SOS</span>
              </motion.button>
            ) : (
              <motion.button
                key="sos"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSOS}
                className="w-32 h-32 rounded-full bg-sos-red border-4 border-red-300/30 flex flex-col items-center justify-center gap-1 shadow-glow-red hover:bg-red-500 transition-colors"
                animate={{ boxShadow: ['0 0 20px rgba(255,45,85,0.4)', '0 0 40px rgba(255,45,85,0.6)', '0 0 20px rgba(255,45,85,0.4)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <AlertTriangle className="w-10 h-10 text-white" />
                <span className="text-sm font-bold text-white tracking-wider">SOS</span>
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* Demo Crash Simulator */}
        <div className="bg-sos-card border border-sos-border rounded-xl p-3 mb-4">
          <div className="text-[10px] font-mono text-sos-amber uppercase tracking-widest mb-2 flex items-center gap-1.5">
            <Zap className="w-3 h-3" />
            Demo Crash Simulator
          </div>
          <div className="grid grid-cols-2 gap-2">
            {CRASH_SCENARIOS.map((scenario) => (
              <motion.button
                key={scenario.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSimulateCrash(scenario.id)}
                className="flex items-center gap-2 px-2 py-2 rounded-lg bg-sos-surface border border-sos-border hover:border-sos-amber/40 transition-all text-left"
              >
                <span className="text-lg">{scenario.icon}</span>
                <span className="text-[11px] text-sos-text-dim">{scenario.label}</span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* Nearby Hospitals */}
        <div className="bg-sos-card border border-sos-border rounded-xl p-3 mb-4">
          <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-2 flex items-center gap-1.5">
            <Building2 className="w-3 h-3" />
            Nearest Hospitals
          </div>
          <div className="space-y-2">
            {MOCK_HOSPITALS.map((hosp, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-sos-surface border border-sos-border">
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-medium text-sos-text truncate">{hosp.name}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-sos-text-dim">{hosp.distance}</span>
                    <span className="text-[10px] text-sos-cyan">{hosp.eta}</span>
                    <span className="text-[10px] text-sos-green">ICU: {hosp.icu}</span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-0.5 flex-shrink-0 ml-2">
                  <div className="text-sm font-bold font-mono text-sos-green">{hosp.score}</div>
                  <div className="text-[9px] text-sos-text-muted">SCORE</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Emergency Contacts */}
        <div className="bg-sos-card border border-sos-border rounded-xl p-3">
          <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-2 flex items-center gap-1.5">
            <Phone className="w-3 h-3" />
            Emergency Contacts
          </div>
          <div className="space-y-2">
            {MOCK_CONTACTS.map((contact, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-sos-surface border border-sos-border">
                <div>
                  <div className="text-[11px] font-medium text-sos-text">{contact.name}</div>
                  <div className="text-[10px] text-sos-text-dim">{contact.relation} · {contact.phone}</div>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-2 py-1 rounded bg-sos-cyan/10 border border-sos-cyan/30 text-[10px] text-sos-cyan font-mono"
                >
                  NOTIFY
                </motion.button>
              </div>
            ))}
          </div>
        </div>

        {/* Offline mode indicator */}
        {isOfflineMode && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-3 rounded-xl bg-sos-red/10 border border-sos-red/30"
          >
            <div className="flex items-center gap-2 text-sos-red text-xs">
              <WifiOff className="w-4 h-4" />
              <div>
                <div className="font-semibold">Offline Mode Active</div>
                <div className="text-[11px] text-sos-red/70 mt-0.5">
                  Showing last known data. SOS will be queued and sent when connectivity is restored.
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
