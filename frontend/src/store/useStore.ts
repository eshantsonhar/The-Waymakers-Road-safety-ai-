import { create } from 'zustand';
import type {
  Incident, Ambulance, Hospital, ConnectionStatus,
  IncidentStats, HospitalStats, AmbulanceStats, Blackspot
} from '../types';

// ── Route geometry for a dispatched ambulance ────────────────────────────────
export interface ActiveRoute {
  ambulanceId: string;
  vehicleNumber: string;
  ambulanceType: string;
  incidentId: string;
  incidentNumber: string;
  // Current ambulance position
  currentLat: number;
  currentLon: number;
  heading: number;
  speedKmh: number;
  // Route geometry — store both phases' geometry for full route display
  routeToScene: [number, number][];      // [lat, lon] pairs
  routeToHospital: [number, number][];   // [lat, lon] pairs
  routeSource: string;                   // 'osrm' | 'straight_line'
  // Phase
  phase: 'to_scene' | 'to_hospital' | 'at_scene' | 'at_hospital';
  routeProgress: number;                 // 0.0 – 1.0
  etaMinutes: number;
  // Hospital info
  hospitalId: string;
  hospitalName: string;
  hospitalSelectionReason: string;
  hospitalLat: number;
  hospitalLon: number;
  // Route label for legend
  label: string;
}

// ── Route reconstruction type from state snapshot ────────────────────────────
export interface RouteReconstruction {
  ambulance_id: string;
  incident_id: string;
  incident_number: string;
  route_type: string;
  geometry: [number, number][];
  current_lat: number;
  current_lon: number;
  heading: number;
  progress: number;
  hospital_name: string;
  hospital_id: string;
}

interface RoadSoSState {
  // Connection
  wsStatus: ConnectionStatus;
  setWsStatus: (status: ConnectionStatus) => void;

  // Incidents
  incidents: Incident[];
  addIncident: (incident: Incident) => void;
  updateIncident: (id: string, updates: Partial<Incident>) => void;
  resolveIncident: (id: string) => void;
  selectedIncidentId: string | null;
  setSelectedIncident: (id: string | null) => void;

  // Ambulances
  ambulances: Ambulance[];
  setAmbulances: (ambulances: Ambulance[]) => void;
  updateAmbulancePosition: (id: string, lat: number, lon: number, heading: number, speed: number) => void;
  updateAmbulanceStatus: (id: string, status: string) => void;

  // Active routes (the core of the map story)
  activeRoutes: Record<string, ActiveRoute>;
  setActiveRoute: (ambulanceId: string, route: ActiveRoute) => void;
  updateRoutePosition: (ambulanceId: string, lat: number, lon: number, heading: number, speed: number, progress: number, eta: number, phase: string) => void;
  // Route reconstruction from snapshot
  setRoutesFromReconstruction: (routes: RouteReconstruction[], ambulances: Ambulance[], incidents: Incident[]) => void;
  removeRoute: (ambulanceId: string) => void;

  // Hospitals
  hospitals: Hospital[];
  setHospitals: (hospitals: Hospital[]) => void;
  updateHospitalLoad: (index: number, updates: Partial<Hospital>) => void;

  // Stats
  incidentStats: IncidentStats | null;
  setIncidentStats: (stats: IncidentStats) => void;
  hospitalStats: HospitalStats | null;
  setHospitalStats: (stats: HospitalStats) => void;
  ambulanceStats: AmbulanceStats | null;
  setAmbulanceStats: (stats: AmbulanceStats) => void;

  // Heatmap
  heatmapData: GeoJSON.FeatureCollection | null;
  setHeatmapData: (data: GeoJSON.FeatureCollection) => void;
  blackspots: Blackspot[];
  setBlackspots: (blackspots: Blackspot[]) => void;

  // UI State
  activeView: 'command' | 'citizen' | 'admin';
  setActiveView: (view: 'command' | 'citizen' | 'admin') => void;
  showHeatmap: boolean;
  toggleHeatmap: () => void;
  showAmbulances: boolean;
  toggleAmbulances: () => void;
  showHospitals: boolean;
  toggleHospitals: () => void;
  showRoutes: boolean;
  toggleRoutes: () => void;
  isOfflineMode: boolean;
  toggleOfflineMode: () => void;

  // Notifications
  notifications: AppNotification[];
  addNotification: (notification: AppNotification) => void;
  dismissNotification: (id: string) => void;

  // Demo
  isDemoMode: boolean;
  setDemoMode: (enabled: boolean) => void;
}

export interface AppNotification {
  id: string;
  type: 'incident' | 'ambulance' | 'hospital' | 'system' | 'alert';
  title: string;
  message: string;
  severity?: string;
  timestamp: string;
  read: boolean;
}

export const useStore = create<RoadSoSState>((set) => ({
  // Connection
  wsStatus: 'connecting',
  setWsStatus: (status) => set({ wsStatus: status }),

  // Incidents
  incidents: [],
  addIncident: (incident) =>
    set((state) => ({
      incidents: [incident, ...state.incidents].slice(0, 100),
    })),
  updateIncident: (id, updates) =>
    set((state) => ({
      incidents: state.incidents.map((inc) =>
        inc.id === id ? { ...inc, ...updates } : inc
      ),
    })),
  resolveIncident: (id) =>
    set((state) => ({
      incidents: state.incidents.map((inc) =>
        inc.id === id ? { ...inc, status: 'RESOLVED' as const } : inc
      ),
    })),
  selectedIncidentId: null,
  setSelectedIncident: (id) => set({ selectedIncidentId: id }),

  // Ambulances
  ambulances: [],
  setAmbulances: (ambulances) => set({ ambulances }),
  updateAmbulancePosition: (id, lat, lon, heading, speed) =>
    set((state) => ({
      ambulances: state.ambulances.map((amb) =>
        amb.id === id
          ? { ...amb, latitude: lat, longitude: lon, heading, speed_kmh: speed }
          : amb
      ),
    })),
  updateAmbulanceStatus: (id, status) =>
    set((state) => ({
      ambulances: state.ambulances.map((amb) =>
        amb.id === id ? { ...amb, status: status as Ambulance['status'] } : amb
      ),
    })),

  // Active routes
  activeRoutes: {},
  setActiveRoute: (ambulanceId, route) =>
    set((state) => ({
      activeRoutes: { ...state.activeRoutes, [ambulanceId]: route },
    })),
  updateRoutePosition: (ambulanceId, lat, lon, heading, speed, progress, eta, phase) =>
    set((state) => {
      const existing = state.activeRoutes[ambulanceId];
      if (!existing) return state;
      return {
        activeRoutes: {
          ...state.activeRoutes,
          [ambulanceId]: {
            ...existing,
            currentLat: lat,
            currentLon: lon,
            heading,
            speedKmh: speed,
            routeProgress: progress,
            etaMinutes: eta,
            phase: phase as ActiveRoute['phase'],
          },
        },
      };
    }),
  setRoutesFromReconstruction: (routes, ambulances, incidents) =>
    set((state) => {
      const activeRoutes: Record<string, ActiveRoute> = {};
      for (const rr of routes) {
        const amb = ambulances.find(a => a.id === rr.ambulance_id);
        const inc = incidents.find(i => i.id === rr.incident_id);
        const isToHospital = rr.route_type === 'to_hospital';
        activeRoutes[rr.ambulance_id] = {
          ambulanceId: rr.ambulance_id,
          vehicleNumber: amb?.vehicle_number ?? rr.ambulance_id,
          ambulanceType: amb?.ambulance_type ?? 'ALS',
          incidentId: rr.incident_id,
          incidentNumber: rr.incident_number,
          currentLat: rr.current_lat,
          currentLon: rr.current_lon,
          heading: rr.heading,
          speedKmh: amb?.speed_kmh ?? 0,
          routeToScene: isToHospital ? [] : rr.geometry,
          routeToHospital: isToHospital ? rr.geometry : (inc?.route_to_hospital ?? []),
          routeSource: 'osrm',
          phase: isToHospital ? 'to_hospital' : 'to_scene',
          routeProgress: rr.progress,
          etaMinutes: isToHospital
            ? (amb?.eta_to_hospital_minutes ?? 0)
            : (amb?.eta_to_scene_minutes ?? 0),
          hospitalId: rr.hospital_id,
          hospitalName: rr.hospital_name,
          hospitalSelectionReason: inc?.hospital_selection_reason ?? '',
          hospitalLat: 0,
          hospitalLon: 0,
          label: `${amb?.call_sign ?? 'AMB'} → ${rr.hospital_name}`,
        };
      }
      return { activeRoutes };
    }),
  removeRoute: (ambulanceId) =>
    set((state) => {
      const next = { ...state.activeRoutes };
      delete next[ambulanceId];
      return { activeRoutes: next };
    }),

  // Hospitals
  hospitals: [],
  setHospitals: (hospitals) => set({ hospitals }),
  updateHospitalLoad: (index, updates) =>
    set((state) => ({
      hospitals: state.hospitals.map((h, i) =>
        i === index ? { ...h, ...updates } : h
      ),
    })),

  // Stats
  incidentStats: null,
  setIncidentStats: (stats) => set({ incidentStats: stats }),
  hospitalStats: null,
  setHospitalStats: (stats) => set({ hospitalStats: stats }),
  ambulanceStats: null,
  setAmbulanceStats: (stats) => set({ ambulanceStats: stats }),

  // Heatmap
  heatmapData: null,
  setHeatmapData: (data) => set({ heatmapData: data }),
  blackspots: [],
  setBlackspots: (blackspots) => set({ blackspots }),

  // UI State
  activeView: 'command',
  setActiveView: (view) => set({ activeView: view }),
  showHeatmap: true,
  toggleHeatmap: () => set((state) => ({ showHeatmap: !state.showHeatmap })),
  showAmbulances: true,
  toggleAmbulances: () => set((state) => ({ showAmbulances: !state.showAmbulances })),
  showHospitals: true,
  toggleHospitals: () => set((state) => ({ showHospitals: !state.showHospitals })),
  showRoutes: true,
  toggleRoutes: () => set((state) => ({ showRoutes: !state.showRoutes })),
  isOfflineMode: false,
  toggleOfflineMode: () => set((state) => ({ isOfflineMode: !state.isOfflineMode })),

  // Notifications
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 50),
    })),
  dismissNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  // Demo
  isDemoMode: true,
  setDemoMode: (enabled) => set({ isDemoMode: enabled }),
}));
