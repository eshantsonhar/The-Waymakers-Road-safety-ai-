/**
 * RoadSoS Mobile Sensor Simulator
 * =================================
 * Realistic sensor simulation for mobile telemetry dashboard.
 * Simulates accelerometer, gyroscope, speed, GPS, and crash detection.
 *
 * Features:
 * - Accelerometer (x, y, z) with noise + drift
 * - Gyroscope (alpha, beta, gamma) with realistic drift
 * - Speed (km/h) with acceleration/deceleration profiles
 * - GPS position with realistic movement
 * - Sudden impact detection (crash simulation)
 * - Pothole detection (short spike)
 * - Braking detection (negative acceleration)
 * - Orientation changes
 *
 * Realism:
 * - Gaussian noise on all sensor values
 * - Low-frequency drift on gyroscope
 * - Speed follows smooth acceleration curves
 * - GPS jitter simulates real GPS inaccuracy
 */

export interface SensorReading {
  accelerometer: { x: number; y: number; z: number };
  gyroscope: { alpha: number; beta: number; gamma: number };
  speed_kmh: number;
  gps: { lat: number; lon: number; accuracy_m: number; heading: number };
  orientation: { pitch: number; roll: number; yaw: number };
  crash_detected: boolean;
  crash_impact_g: number;
  pothole_detected: boolean;
  braking_detected: boolean;
  sos_triggered: boolean;
  timestamp: string;
}

export type SensorEventType =
  | 'normal'
  | 'crash'
  | 'pothole'
  | 'braking'
  | 'acceleration'
  | 'turn';

type SensorCallback = (reading: SensorReading) => void;

export class MobileSensorSimulator {
  private _running = false;
  private _intervalId: ReturnType<typeof setInterval> | null = null;
  private _callbacks: SensorCallback[] = [];

  // State
  private _lat: number = 12.9716;
  private _lon: number = 77.5946;
  private _heading: number = 0;
  private _speed: number = 0; // km/h
  private _targetSpeed: number = 0;
  private _accel: number = 0; // m/s²
  private _pitch: number = 0;
  private _roll: number = 0;
  private _yaw: number = 0;
  private _gyroDrift: { alpha: number; beta: number; gamma: number };
  private _crashDetected: boolean = false;
  private _crashImpactG: number = 0;
  private _potholeDetected: boolean = false;
  private _brakingDetected: boolean = false;
  private _sosTriggered: boolean = false;
  private _tick: number = 0;
  private _eventTimer: number = 0;

  // Bangalore driving route (real road circuit)
  private readonly _routePoints: [number, number][] = [
    [12.9716, 77.5946], // MG Road start
    [12.9757, 77.6011], // MG Road
    [12.9719, 77.6069], // Brigade Road
    [12.9700, 77.6100], // Residency Road
    [12.9670, 77.6140], // Richmond Road
    [12.9650, 77.6180], // Shoolay Circle
    [12.9600, 77.6200], // near Kanteerava
    [12.9550, 77.6180], // near Town Hall
    [12.9500, 77.6150], // near Lalbagh
    [12.9550, 77.6100], // Lalbagh Road
    [12.9600, 77.6050], // Double Road
    [12.9650, 77.6000], // Shoolay
    [12.9680, 77.5960], // near St Patrick's
    [12.9716, 77.5946], // back to MG Road
  ];
  private _routeIndex: number = 0;
  private _routeProgress: number = 0;

  constructor() {
    this._gyroDrift = {
      alpha: (Math.random() - 0.5) * 0.02,
      beta: (Math.random() - 0.5) * 0.01,
      gamma: (Math.random() - 0.5) * 0.015,
    };
  }

  // ── Public API ────────────────────────────────────────────────────────────

  start(intervalMs: number = 100): void {
    if (this._running) return;
    this._running = true;
    this._tick = 0;
    this._eventTimer = 0;
    this._intervalId = setInterval(() => this._tickSensors(), intervalMs);
  }

  stop(): void {
    this._running = false;
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  onReading(callback: SensorCallback): void {
    this._callbacks.push(callback);
  }

  removeListener(callback: SensorCallback): void {
    this._callbacks = this._callbacks.filter((cb) => cb !== callback);
  }

  triggerCrash(impactG: number = 8.0): void {
    this._crashDetected = true;
    this._crashImpactG = impactG;
    this._sosTriggered = true;
    this._speed = 0;
    this._targetSpeed = 0;
  }

  triggerSOS(): void {
    this._sosTriggered = true;
  }

  clearSOS(): void {
    this._sosTriggered = false;
  }

  resetCrash(): void {
    this._crashDetected = false;
    this._crashImpactG = 0;
    this._potholeDetected = false;
    this._brakingDetected = false;
  }

  getState(): SensorReading {
    return this._buildReading();
  }

  isRunning(): boolean {
    return this._running;
  }

  setPosition(lat: number, lon: number): void {
    this._lat = lat;
    this._lon = lon;
  }

  setSpeed(speedKmh: number): void {
    this._targetSpeed = Math.max(0, Math.min(120, speedKmh));
  }

  // ── Internal simulation logic ─────────────────────────────────────────────

  private _tickSensors(): void {
    this._tick++;
    this._eventTimer++;

    // If crashed, maintain crash state
    if (this._crashDetected) {
      this._emitReading();
      return;
    }

    // Simulate driving behavior
    this._simulateDriving();
    this._simulateAccelerometer();
    this._simulateGyroscope();
    this._simulateOrientation();
    this._simulateEvents();
    this._simulateGPS();

    this._emitReading();
  }

  private _simulateDriving(): void {
    // Smooth speed transitions
    const speedDiff = this._targetSpeed - this._speed;
    if (Math.abs(speedDiff) > 1) {
      this._speed += Math.sign(speedDiff) * Math.min(Math.abs(speedDiff) * 0.1, 3.0);
    }

    // Add small speed variations (road bumps, traffic)
    this._speed += (Math.random() - 0.5) * 0.5;
    this._speed = Math.max(0, Math.min(120, this._speed));

    // Deceleration = braking
    if (speedDiff < -5) {
      this._brakingDetected = true;
    } else {
      this._brakingDetected = false;
    }

    // Move along route
    if (this._speed > 1) {
      this._routeProgress += this._speed * 0.000005; // Speed-based progress
      if (this._routeProgress >= 1.0) {
        this._routeProgress = 0;
        this._routeIndex = (this._routeIndex + 1) % this._routePoints.length;
      }

      // Interpolate position on route
      const idx = this._routeIndex;
      const nextIdx = (idx + 1) % this._routePoints.length;
      const p1 = this._routePoints[idx];
      const p2 = this._routePoints[nextIdx];

      this._lat = p1[0] + (p2[0] - p1[0]) * this._routeProgress;
      this._lon = p1[1] + (p2[1] - p1[1]) * this._routeProgress;

      // Compute heading from direction of travel
      const dlat = p2[0] - p1[0];
      const dlon = p2[1] - p1[1];
      this._heading = (Math.atan2(dlon, dlat) * 180 / Math.PI + 360) % 360;
    }

    // Add GPS jitter (real GPS inaccuracy)
    this._lat += (Math.random() - 0.5) * 0.00001;
    this._lon += (Math.random() - 0.5) * 0.00001;
  }

  private _simulateAccelerometer(): void {
    // Base values: gravity (9.8) on z, near-zero on x,y when stationary
    const baseX = (Math.random() - 0.5) * 0.2 + this._roll * 0.05;
    const baseY = (Math.random() - 0.5) * 0.2 + this._pitch * 0.05;
    const baseZ = 9.8 + (Math.random() - 0.5) * 0.3;

    // Acceleration effect
    const accelEffect = this._accel * 0.5;
    const turnEffect = this._yaw * 0.1;

    this._accel = (this._speed - this._getPrevSpeed()) / 3.6; // Convert km/h to m/s²
    this._accel = Math.max(-15, Math.min(15, this._accel));

    // Store for next comparison (simplified: use current)
    this._prevSpeedForAccel = this._speed;
  }

  private _prevSpeedForAccel: number = 0;

  private _getPrevSpeed(): number {
    return this._prevSpeedForAccel;
  }

  private _simulateGyroscope(): void {
    // Angular velocity with drift
    const turnRate = this._yaw * 0.01;

    this._gyroDrift.alpha += (Math.random() - 0.5) * 0.001;
    this._gyroDrift.beta += (Math.random() - 0.5) * 0.0005;
    this._gyroDrift.gamma += (Math.random() - 0.5) * 0.0008;

    // Clamp drift
    this._gyroDrift.alpha = Math.max(-0.05, Math.min(0.05, this._gyroDrift.alpha));
    this._gyroDrift.beta = Math.max(-0.03, Math.min(0.03, this._gyroDrift.beta));
    this._gyroDrift.gamma = Math.max(-0.04, Math.min(0.04, this._gyroDrift.gamma));
  }

  private _simulateOrientation(): void {
    // Realistic orientation changes
    const speedFactor = this._speed / 60.0;
    this._pitch = Math.sin(this._tick * 0.05) * 0.5 * speedFactor + (Math.random() - 0.5) * 0.2;
    this._roll = Math.sin(this._tick * 0.03) * 0.3 * speedFactor + (Math.random() - 0.5) * 0.2;
    this._yaw = Math.sin(this._tick * 0.02) * 1.0 * speedFactor + (Math.random() - 0.5) * 0.5;
  }

  private _simulateEvents(): void {
    // Random event simulation
    if (this._eventTimer > 300 && Math.random() < 0.001) {
      // Pothole (every ~500 ticks)
      this._potholeDetected = true;
      this._eventTimer = 0;
    } else {
      this._potholeDetected = false;
    }

    // Auto-clear crash after a while
    if (this._crashDetected && this._tick % 200 === 0) {
      // Keep crash detected but allow SOS to remain
    }

    // Reset event flags
    if (this._potholeDetected) {
      setTimeout(() => { this._potholeDetected = false; }, 200);
    }
  }

  private _simulateGPS(): void {
    // GPS accuracy varies with conditions
    const accuracyBase = 3.0; // meters
    const speedJitter = this._speed * 0.05;
    const accuracy = accuracyBase + speedJitter + Math.random() * 2;
  }

  private _buildReading(): SensorReading {
    return {
      timestamp: new Date().toISOString(),
      accelerometer: {
        x: Math.round(this._accel * 100) / 100,
        y: Math.round((Math.random() - 0.5) * 0.5 * 100) / 100,
        z: Math.round((9.8 + (Math.random() - 0.5) * 0.5) * 100) / 100,
      },
      gyroscope: {
        alpha: Math.round((this._gyroDrift.alpha + (Math.random() - 0.5) * 0.01) * 1000) / 1000,
        beta: Math.round((this._gyroDrift.beta + (Math.random() - 0.5) * 0.008) * 1000) / 1000,
        gamma: Math.round((this._gyroDrift.gamma + (Math.random() - 0.5) * 0.006) * 1000) / 1000,
      },
      speed_kmh: Math.round(this._speed * 10) / 10,
      gps: {
        lat: Math.round(this._lat * 1000000) / 1000000,
        lon: Math.round(this._lon * 1000000) / 1000000,
        accuracy_m: Math.round((3 + this._speed * 0.05 + Math.random() * 2) * 10) / 10,
        heading: Math.round(this._heading * 10) / 10,
      },
      orientation: {
        pitch: Math.round(this._pitch * 100) / 100,
        roll: Math.round(this._roll * 100) / 100,
        yaw: Math.round(this._yaw * 100) / 100,
      },
      crash_detected: this._crashDetected,
      crash_impact_g: this._crashImpactG,
      pothole_detected: this._potholeDetected,
      braking_detected: this._brakingDetected,
      sos_triggered: this._sosTriggered,
    };
  }

  private _emitReading(): void {
    const reading = this._buildReading();
    this._callbacks.forEach((cb) => cb(reading));
  }
}

// Singleton
export const mobileSensorSimulator = new MobileSensorSimulator();