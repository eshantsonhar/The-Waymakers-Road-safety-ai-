import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useStore } from '../store/useStore';
import type { Incident, Ambulance } from '../types';

// Fix Leaflet default icon issue with Vite
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom icons
const createIncidentIcon = (severity: string) => {
  const colors: Record<string, string> = {
    CRITICAL: '#ff2d55',
    HIGH: '#ff6600',
    MEDIUM: '#ff9500',
    LOW: '#30d158',
  };
  const color = colors[severity] || '#ff9500';

  return L.divIcon({
    html: `
      <div style="
        width: 24px; height: 24px;
        background: ${color};
        border: 2px solid white;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        box-shadow: 0 0 12px ${color}80;
      "></div>
    `,
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
  });
};

const ambulanceIcon = L.divIcon({
  html: `
    <div style="
      width: 20px; height: 20px;
      background: #00d4ff;
      border: 2px solid white;
      border-radius: 4px;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 10px #00d4ff80;
      font-size: 10px;
    ">🚑</div>
  `,
  className: '',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

const hospitalIcon = L.divIcon({
  html: `
    <div style="
      width: 20px; height: 20px;
      background: #30d158;
      border: 2px solid white;
      border-radius: 4px;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 10px #30d15880;
      font-size: 10px;
    ">🏥</div>
  `,
  className: '',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

// Bangalore center
const BANGALORE_CENTER: [number, number] = [12.9716, 77.5946];

function HeatmapLayer() {
  const { heatmapData, showHeatmap } = useStore();
  const map = useMap();

  useEffect(() => {
    if (!heatmapData || !showHeatmap) return;

    const layers: L.Polyline[] = [];

    heatmapData.features.forEach((feature) => {
      if (feature.geometry.type === 'LineString') {
        const coords = feature.geometry.coordinates as [number, number][];
        const latLngs = coords.map(([lon, lat]) => [lat, lon] as [number, number]);
        const riskScore = (feature.properties?.risk_score as number) || 0;
        const color = (feature.properties?.risk_color as string) || '#00FF00';

        const line = L.polyline(latLngs, {
          color,
          weight: riskScore >= 70 ? 5 : riskScore >= 40 ? 3 : 2,
          opacity: 0.7,
        });

        line.bindPopup(`
          <div style="color: #e8eaf6; font-family: monospace; font-size: 12px;">
            <strong>${feature.properties?.name || 'Road Segment'}</strong><br/>
            Risk Score: <span style="color: ${color}">${riskScore.toFixed(0)}/100</span><br/>
            Level: ${feature.properties?.risk_level || 'UNKNOWN'}<br/>
            District: ${feature.properties?.district || 'N/A'}
          </div>
        `);

        line.addTo(map);
        layers.push(line);
      }
    });

    return () => {
      layers.forEach((l) => map.removeLayer(l));
    };
  }, [heatmapData, showHeatmap, map]);

  return null;
}

interface LiveMapProps {
  height?: string;
  showControls?: boolean;
}

export function LiveMap({ height = '100%', showControls = true }: LiveMapProps) {
  const { incidents, ambulances, hospitals, showAmbulances, showHospitals, setSelectedIncident } = useStore();

  const activeIncidents = incidents.filter((i) => i.status !== 'RESOLVED' && i.status !== 'FALSE_ALARM');

  return (
    <div style={{ height }} className="relative rounded-lg overflow-hidden border border-sos-border">
      <MapContainer
        center={BANGALORE_CENTER}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        zoomControl={showControls}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        {/* Heatmap overlay */}
        <HeatmapLayer />

        {/* Active Incidents */}
        {activeIncidents.map((incident) => (
          <Marker
            key={incident.id}
            position={[incident.latitude, incident.longitude]}
            icon={createIncidentIcon(incident.severity)}
            eventHandlers={{
              click: () => setSelectedIncident(incident.id),
            }}
          >
            <Popup>
              <div style={{ color: '#e8eaf6', fontFamily: 'monospace', fontSize: '12px', minWidth: '200px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{incident.incident_number}</div>
                <div>Severity: <span style={{ color: incident.severity === 'CRITICAL' ? '#ff2d55' : incident.severity === 'HIGH' ? '#ff6600' : '#ff9500' }}>{incident.severity}</span></div>
                <div>Status: {incident.status}</div>
                <div style={{ fontSize: '11px', color: '#8892b0', marginTop: '4px' }}>{incident.address}</div>
                {incident.ambulance_eta_minutes && (
                  <div style={{ color: '#00d4ff', marginTop: '4px' }}>🚑 ETA: {incident.ambulance_eta_minutes.toFixed(0)} min</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Ambulances */}
        {showAmbulances && ambulances.filter((a) => a.latitude && a.longitude).map((amb) => (
          <Marker
            key={amb.id}
            position={[amb.latitude, amb.longitude]}
            icon={ambulanceIcon}
          >
            <Popup>
              <div style={{ color: '#e8eaf6', fontFamily: 'monospace', fontSize: '12px' }}>
                <div style={{ fontWeight: 'bold' }}>{amb.vehicle_number}</div>
                <div>Type: {amb.ambulance_type}</div>
                <div>Status: <span style={{ color: '#00d4ff' }}>{amb.status}</span></div>
                <div>Speed: {amb.speed_kmh?.toFixed(0) || 0} km/h</div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Hospitals */}
        {showHospitals && hospitals.filter((h) => h.latitude && h.longitude).slice(0, 20).map((hosp) => (
          <Marker
            key={hosp.id}
            position={[hosp.latitude, hosp.longitude]}
            icon={hospitalIcon}
          >
            <Popup>
              <div style={{ color: '#e8eaf6', fontFamily: 'monospace', fontSize: '12px' }}>
                <div style={{ fontWeight: 'bold' }}>{hosp.name}</div>
                <div>Trauma Level: {hosp.trauma_level}</div>
                <div>ICU Available: <span style={{ color: '#30d158' }}>{hosp.available_icu_beds}</span>/{hosp.total_icu_beds}</div>
                <div>Status: {hosp.is_on_alert ? <span style={{ color: '#ff9500' }}>ON ALERT</span> : <span style={{ color: '#30d158' }}>NORMAL</span>}</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Map overlay info */}
      <div className="absolute top-2 left-2 z-[1000] flex flex-col gap-1">
        <div className="bg-sos-surface/90 border border-sos-border rounded px-2 py-1 text-[10px] font-mono text-sos-text-dim">
          📍 Bangalore, Karnataka
        </div>
        <div className="bg-sos-surface/90 border border-sos-border rounded px-2 py-1 text-[10px] font-mono text-sos-red">
          🔴 {activeIncidents.length} Active Incidents
        </div>
      </div>
    </div>
  );
}
