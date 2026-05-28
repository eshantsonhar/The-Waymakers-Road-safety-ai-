import { useEffect, useRef, useCallback } from 'react';
import { useStore, type RouteReconstruction } from '../store/useStore';
import type { WSMessage, Incident, Ambulance } from '../types';

const WS_URL = `ws://${window.location.hostname}:8000/ws`;

// Exponential backoff: 2s, 4s, 8s, 16s, max 30s
const RECONNECT_BASE_MS = 2000;
const RECONNECT_MAX_MS = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const attemptRef = useRef(0);

  const {
    setWsStatus,
    addIncident,
    updateIncident,
    resolveIncident,
    setAmbulances,
    updateAmbulancePosition,
    updateAmbulanceStatus,
    updateHospitalLoad,
    addNotification,
    setActiveRoute,
    updateRoutePosition,
    removeRoute,
    setHospitals,
    setRoutesFromReconstruction,
  } = useStore();

  const handleMessage = useCallback((message: WSMessage) => {
    const { type, payload } = message;

    switch (type) {
      // ── System ──────────────────────────────────────────────────────────────
      case 'STATE_SNAPSHOT': {
        const snap = payload as {
          active_incidents?: Incident[];
          ambulances?: Ambulance[];
          active_routes?: RouteReconstruction[];
          hospitals?: Array<Record<string, unknown>>;
          demo_mode?: boolean;
          sim_tick?: number;
        };

        // 1. Set ambulances
        if (snap.ambulances) {
          setAmbulances(snap.ambulances);
        }

        // 2. Set incidents
        if (snap.active_incidents) {
          snap.active_incidents.forEach((inc) => addIncident(inc));
        }

        // 3. Set hospitals if provided
        if (snap.hospitals) {
          setHospitals(snap.hospitals as any);
        }

        // 4. Reconstruct active routes from snapshot
        if (snap.active_routes && snap.ambulances && snap.active_incidents) {
          setRoutesFromReconstruction(
            snap.active_routes,
            snap.ambulances,
            snap.active_incidents,
          );
        }
        break;
      }

      // ── Incidents ────────────────────────────────────────────────────────────
      case 'INCIDENT_CREATED': {
        const incident = payload as Incident;
        addIncident(incident);

        addNotification({
          id: `notif-${Date.now()}`,
          type: 'incident' as const,
          title: `🚨 ${incident.incident_number}`,
          message: `${incident.severity} crash at ${incident.address}${incident.assigned_hospital_name ? ` → ${incident.assigned_hospital_name}` : ''}`,
          severity: incident.severity,
          timestamp: new Date().toISOString(),
          read: false,
        });
        break;
      }

      case 'INCIDENT_UPDATED': {
        const update = payload as Partial<Incident> & { id: string };
        updateIncident(update.id, update);
        break;
      }

      case 'INCIDENT_RESOLVED': {
        const resolved = payload as { id: string };
        resolveIncident(resolved.id);
        break;
      }

      // ── Ambulances ───────────────────────────────────────────────────────────
      case 'AMBULANCE_ASSIGNED': {
        const data = payload as {
          ambulance_id: string;
          vehicle_number: string;
          ambulance_type: string;
          incident_id: string;
          incident_number: string;
          latitude: number;
          longitude: number;
          status: string;
          eta_to_scene_minutes: number;
          distance_to_scene_km: number;
          base_station: string;
          route_to_scene: [number, number][];
          route_to_hospital: [number, number][];
          hospital_id: string;
          hospital_name: string;
          hospital_selection_reason: string;
          long_routes?: boolean;
        };

        const { incidents } = useStore.getState();
        const incident = incidents.find((i) => i.id === data.incident_id);

        // Build the active route record
        const route = {
          ambulanceId: data.ambulance_id,
          vehicleNumber: data.vehicle_number,
          ambulanceType: data.ambulance_type,
          incidentId: data.incident_id,
          incidentNumber: data.incident_number,
          currentLat: data.latitude,
          currentLon: data.longitude,
          heading: 0,
          speedKmh: 0,
          routeToScene: data.route_to_scene || [],
          routeToHospital: data.route_to_hospital || [],
          routeSource: 'osrm' as const,
          phase: 'to_scene' as const,
          routeProgress: 0,
          etaMinutes: data.eta_to_scene_minutes,
          hospitalId: data.hospital_id,
          hospitalName: data.hospital_name,
          hospitalSelectionReason: data.hospital_selection_reason || '',
          hospitalLat: data.route_to_hospital?.length ? data.route_to_hospital[data.route_to_hospital.length - 1][0] : 12.9716,
          hospitalLon: data.route_to_hospital?.length ? data.route_to_hospital[data.route_to_hospital.length - 1][1] : 77.5946,
          label: `${data.vehicle_number} → ${data.hospital_name}`,
        };

        setActiveRoute(data.ambulance_id, route);

        addNotification({
          id: `amb-${Date.now()}`,
          type: 'ambulance' as const,
          title: `🚑 ${data.vehicle_number} Dispatched`,
          message: `${data.ambulance_type} unit en route · ETA ${data.eta_to_scene_minutes?.toFixed(0)}min · ${data.hospital_name}`,
          timestamp: new Date().toISOString(),
          read: false,
        });
        break;
      }

      case 'AMBULANCE_POSITION_UPDATE': {
        const data = payload as {
          ambulances: Array<{
            ambulance_id: string;
            latitude: number;
            longitude: number;
            heading: number;
            speed_kmh: number;
            route_progress?: number;
            eta_minutes?: number;
            phase?: string;
          }>;
        };
        data.ambulances?.forEach((amb) => {
          updateAmbulancePosition(amb.ambulance_id, amb.latitude, amb.longitude, amb.heading, amb.speed_kmh);
          updateRoutePosition(
            amb.ambulance_id,
            amb.latitude,
            amb.longitude,
            amb.heading,
            amb.speed_kmh,
            amb.route_progress ?? 0,
            amb.eta_minutes ?? 0,
            amb.phase ?? 'to_scene',
          );
        });
        break;
      }

      case 'AMBULANCE_STATUS_CHANGE': {
        const ambUpdate = payload as {
          ambulance_id: string;
          status: string;
          latitude?: number;
          longitude?: number;
          incident_id?: string;
          hospital_id?: string;
          hospital_name?: string;
          eta_to_hospital_minutes?: number;
        };

        if (ambUpdate.status) {
          updateAmbulanceStatus(ambUpdate.ambulance_id, ambUpdate.status);
        }
        if (ambUpdate.latitude && ambUpdate.longitude) {
          updateAmbulancePosition(ambUpdate.ambulance_id, ambUpdate.latitude, ambUpdate.longitude, 0, 0);
        }

        // Update route phase
        const { activeRoutes } = useStore.getState();
        const existingRoute = activeRoutes[ambUpdate.ambulance_id];
        if (existingRoute) {
          if (ambUpdate.status === 'TRANSPORTING') {
            updateRoutePosition(
              ambUpdate.ambulance_id,
              ambUpdate.latitude ?? existingRoute.currentLat,
              ambUpdate.longitude ?? existingRoute.currentLon,
              existingRoute.heading,
              existingRoute.speedKmh,
              0,
              ambUpdate.eta_to_hospital_minutes ?? existingRoute.etaMinutes,
              'to_hospital',
            );
          } else if (ambUpdate.status === 'AT_HOSPITAL' || ambUpdate.status === 'AVAILABLE') {
            removeRoute(ambUpdate.ambulance_id);
          }
        }
        break;
      }

      // ── Hospitals ────────────────────────────────────────────────────────────
      case 'HOSPITAL_STATUS_UPDATE': {
        const hospData = payload as {
          updates: Array<{
            hospital_id?: string;
            hospital_index?: number;
            available_icu_beds: number;
            current_patient_load: number;
            is_on_alert: boolean;
          }>;
        };
        hospData.updates?.forEach((update) => {
          if (update.hospital_index !== undefined) {
            updateHospitalLoad(update.hospital_index, {
              available_icu_beds: update.available_icu_beds,
              current_patient_load: update.current_patient_load,
              is_on_alert: update.is_on_alert,
            });
          } else if (update.hospital_id) {
            const { hospitals } = useStore.getState();
            const idx = hospitals.findIndex((h: any) => h.id === update.hospital_id);
            if (idx >= 0) {
              updateHospitalLoad(idx, {
                available_icu_beds: update.available_icu_beds,
                current_patient_load: update.current_patient_load,
                is_on_alert: update.is_on_alert,
              });
            }
          }
        });
        break;
      }

      case 'HARDWARE_TELEMETRY': {
        const telemetry = payload as {
          device_id: string;
          latitude: number;
          longitude: number;
          speed_kmh: number;
          crash_detected?: boolean;
          sos_active?: boolean;
        };
        // Log hardware telemetry — can be used to add hardware markers to the map
        break;
      }

      case 'EMERGENCY_ALERT': {
        const alert = payload as { title: string; message: string; severity: string };
        addNotification({
          id: `alert-${Date.now()}`,
          type: 'alert' as const,
          title: alert.title,
          message: alert.message,
          severity: alert.severity,
          timestamp: new Date().toISOString(),
          read: false,
        });
        break;
      }

      default:
        break;
    }
  }, [
    addIncident, updateIncident, resolveIncident,
    setAmbulances, updateAmbulancePosition, updateAmbulanceStatus,
    updateHospitalLoad, addNotification,
    setActiveRoute, updateRoutePosition, removeRoute,
    setHospitals, setRoutesFromReconstruction,
  ]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    setWsStatus('connecting');

    try {
      const ws = new WebSocket(`${WS_URL}/${Date.now()}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setWsStatus('connected');
        attemptRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch {
          // Ignore heartbeat/pong non-JSON messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setWsStatus('disconnected');
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, attemptRef.current),
          RECONNECT_MAX_MS,
        );
        attemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setWsStatus('error');
        ws.close();
      };
    } catch {
      setWsStatus('error');
      const delay = Math.min(
        RECONNECT_BASE_MS * Math.pow(2, attemptRef.current),
        RECONNECT_MAX_MS,
      );
      attemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(connect, delay);
    }
  }, [handleMessage, setWsStatus]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { sendMessage };
}