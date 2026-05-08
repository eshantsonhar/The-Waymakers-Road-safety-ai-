import { useEffect, useCallback } from 'react';
import axios from 'axios';
import { useStore } from '../store/useStore';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

export function useApi() {
  const {
    setAmbulances,
    setHospitals,
    setIncidentStats,
    setHospitalStats,
    setAmbulanceStats,
    setHeatmapData,
    setBlackspots,
    addIncident,
  } = useStore();

  const fetchInitialData = useCallback(async () => {
    try {
      // Fetch ambulances
      const ambRes = await api.get('/api/ambulances/');
      if (ambRes.data.ambulances) {
        setAmbulances(ambRes.data.ambulances);
      }

      // Fetch hospitals
      const hospRes = await api.get('/api/hospitals/');
      if (hospRes.data.hospitals) {
        setHospitals(hospRes.data.hospitals);
      }

      // Fetch incident stats
      const statsRes = await api.get('/api/incidents/stats');
      setIncidentStats(statsRes.data);

      // Fetch hospital stats
      const hospStatsRes = await api.get('/api/hospitals/stats');
      setHospitalStats(hospStatsRes.data);

      // Fetch ambulance stats
      const ambStatsRes = await api.get('/api/ambulances/stats');
      setAmbulanceStats(ambStatsRes.data);

      // Fetch heatmap
      const heatmapRes = await api.get('/api/risk/heatmap');
      setHeatmapData(heatmapRes.data);

      // Fetch blackspots
      const blackspotsRes = await api.get('/api/risk/blackspots?limit=20');
      setBlackspots(blackspotsRes.data.blackspots || []);

      // Fetch recent incidents
      const incidentsRes = await api.get('/api/incidents/?limit=20');
      if (incidentsRes.data.incidents) {
        incidentsRes.data.incidents.forEach((inc: Parameters<typeof addIncident>[0]) => addIncident(inc));
      }
    } catch (error) {
      console.warn('API fetch failed (backend may not be running):', error);
    }
  }, [setAmbulances, setHospitals, setIncidentStats, setHospitalStats, setAmbulanceStats, setHeatmapData, setBlackspots, addIncident]);

  useEffect(() => {
    fetchInitialData();
    // Refresh stats every 30 seconds
    const interval = setInterval(async () => {
      try {
        const statsRes = await api.get('/api/incidents/stats');
        setIncidentStats(statsRes.data);
        const hospStatsRes = await api.get('/api/hospitals/stats');
        setHospitalStats(hospStatsRes.data);
        const ambStatsRes = await api.get('/api/ambulances/stats');
        setAmbulanceStats(ambStatsRes.data);
      } catch {
        // Silently fail
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchInitialData, setIncidentStats, setHospitalStats, setAmbulanceStats]);

  const triggerSOS = useCallback(async (lat: number, lon: number) => {
    const res = await api.post('/api/incidents/', {
      latitude: lat,
      longitude: lon,
      severity: 'HIGH',
      is_manual_sos: true,
      crash_probability_score: 1.0,
      confidence_level: 'HIGH',
      event_classification: 'MANUAL_SOS',
    });
    return res.data;
  }, []);

  const simulateCrash = useCallback(async (scenario: string) => {
    const res = await api.post(`/api/detection/simulate/${scenario}`);
    return res.data;
  }, []);

  const rankHospitals = useCallback(async (lat: number, lon: number, severity: string) => {
    const res = await api.post('/api/hospitals/rank', {
      latitude: lat,
      longitude: lon,
      severity,
    });
    return res.data;
  }, []);

  const getTrends = useCallback(async (days: number = 30) => {
    const res = await api.get(`/api/analytics/trends?days=${days}`);
    return res.data;
  }, []);

  const getDistrictStats = useCallback(async () => {
    const res = await api.get('/api/analytics/district-stats');
    return res.data;
  }, []);

  const getResponseEfficiency = useCallback(async () => {
    const res = await api.get('/api/analytics/response-efficiency');
    return res.data;
  }, []);

  const getInfrastructureInsights = useCallback(async () => {
    const res = await api.get('/api/analytics/infrastructure-insights');
    return res.data;
  }, []);

  return {
    triggerSOS,
    simulateCrash,
    rankHospitals,
    getTrends,
    getDistrictStats,
    getResponseEfficiency,
    getInfrastructureInsights,
    fetchInitialData,
  };
}
