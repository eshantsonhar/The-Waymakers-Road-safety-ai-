import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';
import type { WSMessage, Incident, Ambulance } from '../types';

const WS_URL = `ws://${window.location.hostname}:8000/ws`;
const RECONNECT_DELAY = 3000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

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
  } = useStore();

  const handleMessage = useCallback((message: WSMessage) => {
    const { type, payload } = message;

    switch (type) {
      case 'STATE_SNAPSHOT': {
        const snap = payload as { active_incidents?: Incident[]; ambulances?: Ambulance[] };
        if (snap.ambulances) {
          setAmbulances(snap.ambulances);
        }
        if (snap.active_incidents) {
          snap.active_incidents.forEach((inc) => addIncident(inc));
        }
        break;
      }

      case 'INCIDENT_CREATED': {
        const incident = payload as Incident;
        addIncident(incident);
        addNotification({
          id: `notif-${Date.now()}`,
          type: 'incident',
          title: `🚨 New Incident: ${incident.incident_number}`,
          message: `${incident.severity} severity crash detected at ${incident.address}`,
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

      case 'AMBULANCE_POSITION_UPDATE': {
        const data = payload as { ambulances: Array<{
          ambulance_id: string;
          latitude: number;
          longitude: number;
          heading: number;
          speed_kmh: number;
        }> };
        data.ambulances?.forEach((amb) => {
          updateAmbulancePosition(amb.ambulance_id, amb.latitude, amb.longitude, amb.heading, amb.speed_kmh);
        });
        break;
      }

      case 'AMBULANCE_STATUS_CHANGE':
      case 'AMBULANCE_ASSIGNED': {
        const ambUpdate = payload as { ambulance_id: string; status: string; latitude?: number; longitude?: number };
        if (ambUpdate.status) {
          updateAmbulanceStatus(ambUpdate.ambulance_id, ambUpdate.status);
        }
        if (ambUpdate.latitude && ambUpdate.longitude) {
          updateAmbulancePosition(ambUpdate.ambulance_id, ambUpdate.latitude, ambUpdate.longitude, 0, 0);
        }
        break;
      }

      case 'HOSPITAL_STATUS_UPDATE': {
        const hospData = payload as { updates: Array<{ hospital_index: number; available_icu_beds: number; current_patient_load: number; is_on_alert: boolean }> };
        hospData.updates?.forEach((update) => {
          updateHospitalLoad(update.hospital_index, {
            available_icu_beds: update.available_icu_beds,
            current_patient_load: update.current_patient_load,
            is_on_alert: update.is_on_alert,
          });
        });
        break;
      }

      case 'EMERGENCY_ALERT': {
        const alert = payload as { title: string; message: string; severity: string };
        addNotification({
          id: `alert-${Date.now()}`,
          type: 'alert',
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
  }, [addIncident, updateIncident, resolveIncident, setAmbulances, updateAmbulancePosition, updateAmbulanceStatus, updateHospitalLoad, addNotification]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    setWsStatus('connecting');

    try {
      const ws = new WebSocket(`${WS_URL}/${Date.now()}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setWsStatus('connected');
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (e) {
          // Ignore parse errors for heartbeat messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setWsStatus('disconnected');
        console.log('WebSocket disconnected, reconnecting...');
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setWsStatus('error');
        ws.close();
      };
    } catch (e) {
      setWsStatus('error');
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, [handleMessage, setWsStatus]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { sendMessage };
}
