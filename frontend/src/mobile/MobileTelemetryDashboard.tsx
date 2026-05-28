/**
 * MobileTelemetryDashboard
 * ========================
 * Real-time sensor simulation dashboard for mobile interface.
 * Shows live accelerometer, gyroscope, GPS, speed, crash detection.
 *
 * This is NOT a static UI mock - it shows live streaming values.
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  mobileSensorSimulator,
  type SensorReading,
} from './sensor_simulator';

// ── Sensor value display component ──────────────────────────────────────────
function SensorBar({
  label,
  value,
  unit,
  min,
  max,
  color,
  format,
}: {
  label: string;
  value: number;
  unit: string;
  min?: number;
  max?: number;
  color?: string;
  format?: (v: number) => string;
}) {
  const displayValue = format ? format(value) : value.toFixed(2);
  const pct = min !== undefined && max !== undefined
    ? ((value - min) / (max - min)) * 100
    : 50;

  return (
    <div style={{
      background: 'rgba(15,22,41,0.85)', border: '1px solid #1e2d4a',
      borderRadius: '6px', padding: '6px 8px', marginBottom: '4px',
      fontFamily: 'monospace', fontSize: '11px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
        <span style={{ color: '#8892b0' }}>{label}</span>
        <span style={{ color: color || '#00d4ff', fontWeight: 'bold' }}>
          {displayValue} <span style={{ color: '#4a5568', fontSize: '9px' }}>{unit}</span>
        </span>
      </div>
      {min !== undefined && max !== undefined && (
        <div style={{
          height: '3px', background: '#1e2d4a', borderRadius: '2px',
          overflow: 'hidden', marginTop: '2px',
        }}>
          <div style={{
            width: `${Math.max(0, Math.min(100, pct))}%`,
            height: '100%',
            background: color || '#00d4ff',
            borderRadius: '2px',
            transition: 'width 0.15s ease',
          }} />
        </div>
      )}
    </div>
  );
}

// ── Gauges ───────────────────────────────────────────────────────────────────
function CircularGauge({
  label, value, unit, max, color, size = 60,
}: {
  label: string; value: number; unit: string; max: number; color: string; size?: number;
}) {
  const pct = Math.min(value / max, 1);
  const radius = size * 0.35;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      width: size + 20, fontFamily: 'monospace',
    }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#1e2d4a" strokeWidth={4} />
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.2s ease' }}
        />
      </svg>
      <div style={{
        position: 'relative', marginTop: -size + 10, fontSize: '10px',
        fontWeight: 'bold', color,
      }}>
        {value.toFixed(0)}
      </div>
      <div style={{ fontSize: '8px', color: '#4a5568', marginTop: '2px' }}>{label}</div>
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────────────
export function MobileTelemetryDashboard() {
  const [reading, setReading] = useState<SensorReading | null>(null);
  const [sensorHistory, setSensorHistory] = useState<number[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [targetSpeed, setTargetSpeed] = useState(40);

  useEffect(() => {
    const handler = (r: SensorReading) => {
      setReading(r);
      setSensorHistory((prev) => {
        const next = [...prev, r.speed_kmh];
        return next.slice(-60); // Keep last 60 readings
      });
    };
    mobileSensorSimulator.onReading(handler);
    return () => mobileSensorSimulator.removeListener(handler);
  }, []);

  const toggleSimulation = useCallback(() => {
    if (isSimulating) {
      mobileSensorSimulator.stop();
      setIsSimulating(false);
    } else {
      mobileSensorSimulator.start(100);
      setIsSimulating(true);
    }
  }, [isSimulating]);

  const handleCrash = useCallback(() => {
    mobileSensorSimulator.triggerCrash(9.2);
  }, []);

  const handleSOS = useCallback(() => {
    if (reading?.sos_triggered) {
      mobileSensorSimulator.clearSOS();
    } else {
      mobileSensorSimulator.triggerSOS();
    }
  }, [reading]);

  const handleSpeedChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const s = parseInt(e.target.value, 10);
    setTargetSpeed(s);
    mobileSensorSimulator.setSpeed(s);
  }, []);

  if (!reading) {
    return (
      <div style={{
        background: '#0a0f1e', padding: '16px', borderRadius: '8px',
        fontFamily: 'monospace', color: '#8892b0', textAlign: 'center',
      }}>
        <div style={{ fontSize: '24px', marginBottom: '8px' }}>📱</div>
        <div>Mobile Sensor Simulator</div>
        <button onClick={toggleSimulation} style={startBtnStyle}>
          {isSimulating ? '⏹ Stop' : '▶ Start Simulation'}
        </button>
      </div>
    );
  }

  const sosColor = reading.sos_triggered ? '#ff2d55' : '#4a5568';
  const crashColor = reading.crash_detected ? '#ff2d55' : '#30d158';
  const brakingColor = reading.braking_detected ? '#ff9500' : '#4a5568';
  const potholeColor = reading.pothole_detected ? '#ff6600' : '#4a5568';
  const speedColor = reading.speed_kmh > 80 ? '#ff2d55' : reading.speed_kmh > 50 ? '#ff9500' : '#00d4ff';

  return (
    <div style={{
      background: '#0a0f1e', borderRadius: '12px',
      border: '1px solid #1e2d4a', overflow: 'hidden',
      fontFamily: 'monospace',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', background: 'rgba(15,22,41,0.9)',
        borderBottom: '1px solid #1e2d4a',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: '14px' }}>📱</span>
          <span style={{ color: '#e8eaf6', fontWeight: 'bold', fontSize: '12px', marginLeft: '6px' }}>
            TELEMETRY DASHBOARD
          </span>
        </div>
        <div style={{
          width: '8px', height: '8px', borderRadius: '50%',
          background: isSimulating ? '#30d158' : '#ff2d55',
          boxShadow: isSimulating ? '0 0 6px #30d158' : '0 0 6px #ff2d55',
        }} />
      </div>

      {/* Status badges */}
      <div style={{
        display: 'flex', gap: '4px', padding: '6px 8px',
        background: 'rgba(0,0,0,0.3)',
        flexWrap: 'wrap',
      }}>
        <StatusBadge color={sosColor} active={reading.sos_triggered} label="SOS" />
        <StatusBadge color={crashColor} active={reading.crash_detected} label="CRASH" />
        <StatusBadge color={brakingColor} active={reading.braking_detected} label="BRAKE" />
        <StatusBadge color={potholeColor} active={reading.pothole_detected} label="POTHOLE" />
        <StatusBadge color="#30d158" active={reading.speed_kmh > 0} label="MOVING" />
      </div>

      {/* Gauges row */}
      <div style={{
        display: 'flex', justifyContent: 'space-around', padding: '8px 4px',
        background: 'rgba(0,0,0,0.2)',
      }}>
        <CircularGauge label="SPEED" value={reading.speed_kmh} unit="km/h" max={120} color={speedColor} size={56} />
        <CircularGauge label="IMPACT" value={reading.crash_impact_g} unit="G" max={12} color={crashColor} size={56} />
        <CircularGauge label="ACCEL Z" value={Math.abs(reading.accelerometer.z)} unit="m/s²" max={15} color="#bf5af2" size={56} />
      </div>

      {/* Speed slider */}
      <div style={{ padding: '6px 10px' }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          color: '#8892b0', fontSize: '9px', marginBottom: '4px',
        }}>
          <span>Target Speed</span>
          <span style={{ color: speedColor, fontWeight: 'bold' }}>{targetSpeed} km/h</span>
        </div>
        <input
          type="range" min={0} max={100} value={targetSpeed}
          onChange={handleSpeedChange}
          style={{
            width: '100%', height: '4px', appearance: 'none',
            background: '#1e2d4a', borderRadius: '2px', outline: 'none',
          }}
        />
      </div>

      {/* GPS */}
      <div style={{ padding: '6px 10px', borderTop: '1px solid rgba(30,45,74,0.5)' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px',
          fontSize: '10px', color: '#8892b0',
        }}>
          <div>📍 Lat: <span style={{ color: '#e8eaf6' }}>{reading.gps.lat.toFixed(6)}</span></div>
          <div>Lon: <span style={{ color: '#e8eaf6' }}>{reading.gps.lon.toFixed(6)}</span></div>
          <div>🧭 Heading: <span style={{ color: '#e8eaf6' }}>{reading.gps.heading.toFixed(1)}°</span></div>
          <div>🎯 Accuracy: <span style={{ color: '#30d158' }}>{reading.gps.accuracy_m.toFixed(1)}m</span></div>
        </div>
      </div>

      {/* Accelerometer values */}
      <div style={{ padding: '6px 10px', borderTop: '1px solid rgba(30,45,74,0.5)' }}>
        <div style={{ color: '#4a5568', fontSize: '9px', marginBottom: '4px' }}>ACCELEROMETER (m/s²)</div>
        <SensorBar label="X" value={reading.accelerometer.x} unit="m/s²" min={-10} max={10} color="#ff2d55" />
        <SensorBar label="Y" value={reading.accelerometer.y} unit="m/s²" min={-10} max={10} color="#30d158" />
        <SensorBar label="Z" value={reading.accelerometer.z} unit="m/s²" min={0} max={15} color="#00d4ff" />
      </div>

      {/* Gyroscope values */}
      <div style={{ padding: '6px 10px', borderTop: '1px solid rgba(30,45,74,0.5)' }}>
        <div style={{ color: '#4a5568', fontSize: '9px', marginBottom: '4px' }}>GYROSCOPE (rad/s)</div>
        <SensorBar label="α" value={reading.gyroscope.alpha} unit="rad/s" min={-0.05} max={0.05} color="#bf5af2" />
        <SensorBar label="β" value={reading.gyroscope.beta} unit="rad/s" min={-0.05} max={0.05} color="#ff9500" />
        <SensorBar label="γ" value={reading.gyroscope.gamma} unit="rad/s" min={-0.05} max={0.05} color="#ff2d55" />
      </div>

      {/* Speed history sparkline */}
      <div style={{ padding: '6px 10px', borderTop: '1px solid rgba(30,45,74,0.5)' }}>
        <div style={{ color: '#4a5568', fontSize: '9px', marginBottom: '4px' }}>SPEED HISTORY (last 60 ticks)</div>
        <div style={{ height: '24px', display: 'flex', alignItems: 'flex-end', gap: '1px' }}>
          {sensorHistory.map((s, i) => {
            const h = Math.max(2, (s / 120) * 22);
            return (
              <div key={i} style={{
                flex: 1, height: `${h}px`,
                background: s > 80 ? '#ff2d55' : s > 50 ? '#ff9500' : '#00d4ff',
                borderRadius: '1px 1px 0 0',
                opacity: 0.6 + (i / sensorHistory.length) * 0.4,
              }} />
            );
          })}
        </div>
      </div>

      {/* Action buttons */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px',
        padding: '8px 10px', borderTop: '1px solid #1e2d4a',
      }}>
        <button onClick={toggleSimulation} style={actionBtnStyle}>
          {isSimulating ? '⏹ Stop Sim' : '▶ Start Sim'}
        </button>
        <button onClick={handleCrash} style={{
          ...actionBtnStyle,
          background: 'rgba(255,45,85,0.2)', color: '#ff2d55',
          borderColor: '#ff2d55',
        }}>
          💥 Trigger Crash
        </button>
        <button onClick={handleSOS} style={{
          ...actionBtnStyle,
          background: reading?.sos_triggered ? 'rgba(255,45,85,0.3)' : 'rgba(255,149,0,0.15)',
          color: reading?.sos_triggered ? '#ff2d55' : '#ff9500',
          borderColor: reading?.sos_triggered ? '#ff2d55' : '#ff9500',
        }}>
          {reading?.sos_triggered ? '🔴 CLEAR SOS' : '🆘 TRIGGER SOS'}
        </button>
        <button onClick={() => mobileSensorSimulator.resetCrash()} style={{
          ...actionBtnStyle,
          background: 'rgba(0,212,255,0.1)', color: '#00d4ff',
          borderColor: '#00d4ff',
        }}>
          🔄 Reset Alarms
        </button>
      </div>
    </div>
  );
}

// ── Helper components ────────────────────────────────────────────────────────

function StatusBadge({ color, active, label }: { color: string; active: boolean; label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '4px',
      padding: '2px 6px', borderRadius: '3px',
      background: active ? `${color}22` : 'rgba(30,45,74,0.5)',
      border: `1px solid ${active ? color : '#1e2d4a'}`,
      fontSize: '9px', fontWeight: 'bold',
      color: active ? color : '#4a5568',
      transition: 'all 0.2s ease',
    }}>
      <div style={{
        width: '5px', height: '5px', borderRadius: '50%',
        background: color,
        opacity: active ? 1 : 0.3,
      }} />
      {label}
    </div>
  );
}

const startBtnStyle: React.CSSProperties = {
  marginTop: '12px', padding: '8px 16px',
  background: '#00d4ff', color: '#0a0f1e',
  border: 'none', borderRadius: '6px',
  fontFamily: 'monospace', fontWeight: 'bold', fontSize: '12px',
  cursor: 'pointer',
};

const actionBtnStyle: React.CSSProperties = {
  padding: '6px 8px', borderRadius: '4px',
  border: '1px solid #1e2d4a',
  background: 'rgba(15,22,41,0.8)',
  color: '#8892b0', fontFamily: 'monospace',
  fontSize: '10px', fontWeight: 'bold',
  cursor: 'pointer', textAlign: 'center',
};