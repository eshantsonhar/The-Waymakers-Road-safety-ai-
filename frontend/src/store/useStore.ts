import { create } from 'zustand';
import type {
  Incident, Ambulance, Hospital, ConnectionStatus,
  IncidentStats, HospitalStats, AmbulanceStats, Blackspot
} from '../types';

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

export const useStore = create<RoadSoSState>((set, get) => ({
  // Connection
  wsStatus: 'connecting',
  setWsStatus: (status) => set({ wsStatus: status }),

  // Incidents
  incidents: [],
  addIncident: (incident) =>
    set((state) => ({
      incidents: [incident, ...state.incidents].slice(0, 100), // keep last 100
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
