// ============================================================
// RoadSoS Type Definitions
// ============================================================

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentStatus =
  | 'DETECTED' | 'CONFIRMED' | 'DISPATCHED' | 'EN_ROUTE'
  | 'ON_SCENE' | 'TRANSPORTING' | 'RESOLVED' | 'FALSE_ALARM';
export type AmbulanceStatus =
  | 'AVAILABLE' | 'DISPATCHED' | 'EN_ROUTE_TO_SCENE' | 'ON_SCENE'
  | 'TRANSPORTING' | 'AT_HOSPITAL' | 'RETURNING' | 'OFFLINE' | 'MAINTENANCE';
export type AmbulanceType = 'BLS' | 'ALS' | 'MICU' | 'NEONATAL';

export interface Incident {
  id: string;
  incident_number: string;
  latitude: number;
  longitude: number;
  address: string;
  district: string;
  severity: SeverityLevel;
  status: IncidentStatus;
  crash_probability_score: number;
  confidence_level: string;
  event_classification: string;
  assigned_ambulance_id?: string;
  assigned_hospital_id?: string;
  assigned_hospital_name?: string;
  assigned_hospital_short?: string;
  ambulance_eta_minutes?: number;
  ambulance_distance_km?: number;
  hospital_eta_minutes?: number;
  hospital_distance_km?: number;
  hospital_selection_reason?: string;
  hospital_trauma_level?: number;
  hospital_icu_available?: number;
  // Route geometry (from backend)
  route_to_scene?: [number, number][];
  route_to_hospital?: [number, number][];
  route_source?: string;
  timeline: Record<string, string>;
  is_demo: boolean;
  detected_at: string;
  created_at: string;
  resolved_at?: string;
  vehicle_type?: string;
  weather_condition?: string;
  description?: string;
}

export interface Ambulance {
  id: string;
  vehicle_number: string;
  call_sign: string;
  ambulance_type: AmbulanceType;
  latitude: number;
  longitude: number;
  heading: number;
  speed_kmh: number;
  status: AmbulanceStatus;
  is_active: boolean;
  current_incident_id?: string;
  assigned_hospital_id?: string;
  crew_count: number;
  has_paramedic: boolean;
  has_doctor: boolean;
  base_station_name: string;
  eta_to_scene_minutes?: number;
  eta_to_hospital_minutes?: number;
  current_route: [number, number][];
  route_progress: number;
  last_location_update: string;
  distance_km?: number;
  eta_minutes?: number;
}

export interface Hospital {
  id: string;
  name: string;
  short_name: string;
  latitude: number;
  longitude: number;
  address: string;
  district: string;
  phone: string;
  trauma_level: number;
  has_trauma_center: boolean;
  has_icu: boolean;
  has_cath_lab: boolean;
  has_neurosurgery: boolean;
  total_icu_beds: number;
  available_icu_beds: number;
  total_emergency_beds: number;
  available_emergency_beds: number;
  current_patient_load: number;
  max_patient_load: number;
  available_blood_types: string[];
  active_specialists: string[];
  suitability_score: number;
  load_percentage: number;
  is_active: boolean;
  is_on_alert: boolean;
  accepts_trauma: boolean;
  // Ranking fields
  rank?: number;
  distance_km?: number;
  estimated_travel_minutes?: number;
  recommendation_explanation?: string;
  score_breakdown?: Record<string, number>;
}

export interface RoadSegment {
  id: string;
  name: string;
  road_type: string;
  district: string;
  start_latitude: number;
  start_longitude: number;
  end_latitude: number;
  end_longitude: number;
  length_km: number;
  risk_score: number;
  is_blackspot: boolean;
  prediction_confidence: number;
  accident_frequency_per_year: number;
  total_accidents: number;
  fatal_accidents: number;
  risk_factors: Record<string, number>;
  trend_direction: string;
}

export interface WSMessage {
  type: string;
  channel: string;
  payload: unknown;
  timestamp: string;
}

export interface DetectionResult {
  crash_probability_score: number;
  severity: SeverityLevel;
  confidence_level: string;
  event_classification: string;
  is_crash: boolean;
  is_suspected: boolean;
  impact_force_g: number;
  speed_delta_kmh: number;
  rollover_detected: boolean;
  contributing_signals: string[];
  action_required: string;
  timestamp: string;
}

export interface IncidentStats {
  total_last_24h: number;
  active_incidents: number;
  resolved_last_24h: number;
  severity_distribution: Record<SeverityLevel, number>;
  status_distribution: Record<string, number>;
  avg_response_time_minutes: number;
  fastest_response_minutes: number;
  ambulances_deployed: number;
  hospitals_on_alert: number;
}

export interface HospitalStats {
  total_hospitals: number;
  active_hospitals: number;
  on_alert: number;
  trauma_centers: number;
  total_icu_beds: number;
  available_icu_beds: number;
  icu_occupancy_percent: number;
}

export interface AmbulanceStats {
  total: number;
  available: number;
  deployed: number;
  offline: number;
  status_breakdown: Record<string, number>;
}

export interface TrendDataPoint {
  date: string;
  total_incidents: number;
  fatal: number;
  severe: number;
  moderate: number;
  minor: number;
  avg_response_time_minutes: number;
}

export interface DistrictStat {
  district: string;
  total_incidents: number;
  fatal_incidents: number;
  severe_incidents: number;
  avg_severity_score: number;
  top_blackspot: string;
  avg_response_time_minutes: number;
  blackspot_count: number;
  trend: string;
  fatality_rate_percent: number;
}

export interface Blackspot {
  id: string;
  name: string;
  district: string;
  risk_score: number;
  latitude: number;
  longitude: number;
  trend_direction: string;
  total_accidents: number;
  fatal_accidents: number;
  primary_factor: string;
  contributing_factors: Record<string, number>;
  prediction_confidence: number;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
