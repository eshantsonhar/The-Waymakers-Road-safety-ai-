/**
 * LiveMap — Emergency Operations Map
 *
 * Visual story for every incident:
 *   🔴 Accident marker (orange/red by severity)
 *   🚑 Ambulance marker (cyan/animated along route)
 *   🏥 Hospital marker (green, selected hospital highlighted)
 *   ─── Red polyline: ambulance → accident (road-following)
 *   ─── Blue polyline: accident → hospital (road-following)
 *   ─── Faded grey: risk heatmap segments
 *   🏷️ Route labels: AMB-12 → Accident / AMB-12 → St John's Hospital
 *
 * Focus mode: Click an incident to fade unrelated routes
 *
 * Color system:
 *   Red    = ambulance → scene route
 *   Blue   = scene → hospital route
 *   Orange = accident location
 *   Cyan   = ambulance
 *   Green  = selected hospital
 *   Yellow = risk heatmap (high risk)
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  MapContainer, TileLayer, Marker, Popup,
  Polyline, CircleMarker, useMap, Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import { useStore } from '../store/useStore';
import type { Incident } from '../types';
import type { ActiveRoute } from '../store/useStore';

// ── Fix Leaflet default icon with Vite ───────────────────────────────────────
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const BANGALORE_CENTER: [number, number] = [12.9716, 77.5946];

// ── Custom SVG icons ─────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#ff2d55',
  HIGH:     '#ff6600',
  MEDIUM:   '#ff9500',
  LOW:      '#30d158',
};

function makeIncidentIcon(severity: string, isSelected: boolean) {
  const color = SEVERITY_COLORS[severity] || '#ff9500';
  const size = isSelected ? 36 : 28;
  const pulse = severity === 'CRITICAL' || severity === 'HIGH';
  return L.divIcon({
    html: `
      <div style="position:relative;width:${size}px;height:${size}px;">
        ${pulse ? `<div style="
          position:absolute;inset:0;border-radius:50%;
          background:${color}33;
          animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;
        "></div>` : ''}
        <div style="
          position:absolute;inset:0;
          background:${color};
          border:2px solid white;
          border-radius:50% 50% 50% 0;
          transform:rotate(-45deg);
          box-shadow:0 0 ${isSelected ? 16 : 8}px ${color}99;
        "></div>
        <div style="
          position:absolute;inset:0;
          display:flex;align-items:center;justify-content:center;
          font-size:${size * 0.4}px;
          transform:none;
        ">⚡</div>
      </div>
      <style>
        @keyframes ping {
          75%,100%{transform:scale(2);opacity:0}
        }
      </style>
    `,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

function makeAmbulanceIcon(phase: string, heading: number) {
  const color = phase === 'to_hospital' || phase === 'at_scene' ? '#bf5af2' : '#00d4ff';
  const emoji = '🚑';
  return L.divIcon({
    html: `
      <div style="
        width:32px;height:32px;
        background:${color};
        border:2px solid white;
        border-radius:6px;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 0 12px ${color}99;
        font-size:16px;
        transform:rotate(${heading}deg);
        transition:transform 0.5s ease;
      ">${emoji}</div>
    `,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -20],
  });
}

function makeHospitalIcon(isSelected: boolean) {
  const color = isSelected ? '#30d158' : '#1a7a3a';
  const size = isSelected ? 30 : 22;
  return L.divIcon({
    html: `
      <div style="
        width:${size}px;height:${size}px;
        background:${color};
        border:2px solid white;
        border-radius:4px;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 0 ${isSelected ? 14 : 6}px ${color}99;
        font-size:${size * 0.55}px;
      ">🏥</div>
    `,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2 - 4],
  });
}

// ── Heatmap layer ─────────────────────────────────────────────────────────────
function HeatmapLayer() {
  const { heatmapData, showHeatmap } = useStore();
  const map = useMap();
  const layersRef = useRef<L.Polyline[]>([]);

  useEffect(() => {
    layersRef.current.forEach((l) => map.removeLayer(l));
    layersRef.current = [];

    if (!heatmapData || !showHeatmap) return;

    heatmapData.features.forEach((feature) => {
      if (feature.geometry.type !== 'LineString') return;
      const coords = feature.geometry.coordinates as [number, number][];
      const latLngs = coords.map(([lon, lat]) => [lat, lon] as [number, number]);
      const risk = (feature.properties?.risk_score as number) || 0;
      const color = (feature.properties?.risk_color as string) || '#00FF00';

      const line = L.polyline(latLngs, {
        color,
        weight: risk >= 80 ? 5 : risk >= 60 ? 3.5 : risk >= 40 ? 2.5 : 1.5,
        opacity: risk >= 70 ? 0.75 : 0.45,
        dashArray: risk < 40 ? '4 6' : undefined,
      });

      line.bindTooltip(
        `<div style="font-family:monospace;font-size:11px;color:#e8eaf6;background:#141d35;padding:4px 8px;border-radius:4px;border:1px solid #1e2d4a;">
          <strong>${feature.properties?.name || 'Road Segment'}</strong><br/>
          Risk: <span style="color:${color};font-weight:bold">${risk.toFixed(0)}/100</span>
          &nbsp;&middot;&nbsp;${feature.properties?.risk_level || ''}
        </div>`,
        { sticky: true, opacity: 1, className: 'leaflet-tooltip-dark' }
      );

      line.addTo(map);
      layersRef.current.push(line);
    });

    return () => {
      layersRef.current.forEach((l) => map.removeLayer(l));
      layersRef.current = [];
    };
  }, [heatmapData, showHeatmap, map]);

  return null;
}

// ── Auto-zoom to selected incident ───────────────────────────────────────────
function MapController() {
  const { selectedIncidentId, incidents, activeRoutes } = useStore();
  const map = useMap();

  useEffect(() => {
    if (!selectedIncidentId) return;
    const inc = incidents.find((i) => i.id === selectedIncidentId);
    if (!inc) return;

    const route = Object.values(activeRoutes).find((r) => r.incidentId === selectedIncidentId);

    if (route && (route.routeToScene.length > 0 || route.routeToHospital.length > 0)) {
      const allPoints: [number, number][] = [
        [inc.latitude, inc.longitude],
        [route.currentLat, route.currentLon],
        ...route.routeToScene,
        ...route.routeToHospital,
      ];
      const bounds = L.latLngBounds(allPoints);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
    } else {
      map.setView([inc.latitude, inc.longitude], 14, { animate: true });
    }
  }, [selectedIncidentId, incidents, activeRoutes, map]);

  return null;
}

// ── Route overlay for one active incident ────────────────────────────────────
function RouteOverlay({ route, incident, isFocused }: { route: ActiveRoute; incident: Incident | undefined; isFocused: boolean }) {
  const { showRoutes } = useStore();
  if (!showRoutes) return null;

  const isToScene = route.phase === 'to_scene';
  const isToHospital = route.phase === 'to_hospital';

  // If not focused, fade everything
  const baseOpacity = isFocused ? 1.0 : 0.2;
  const sceneOpacity = isToScene ? baseOpacity * 0.9 : baseOpacity * 0.3;
  const hospitalOpacity = isToHospital ? baseOpacity * 0.9 : baseOpacity * 0.4;

  return (
    <>
      {/* Route label at midpoint of scene route */}
      {route.routeToScene.length > 3 && (
        <Polyline
          positions={route.routeToScene}
          pathOptions={{
            color: '#ff2d55',
            weight: isToScene ? 4 : 2,
            opacity: sceneOpacity,
            dashArray: isToScene ? undefined : '6 8',
          }}
        >
          <Tooltip permanent direction="top" offset={[0, -10]} className="route-label-tooltip">
            <span style={{
              fontFamily: 'monospace', fontSize: '10px', fontWeight: 'bold',
              color: '#ff2d55', background: 'rgba(15,22,41,0.9)',
              padding: '2px 6px', borderRadius: '3px',
              border: '1px solid #ff2d55',
              whiteSpace: 'nowrap',
            }}>
              🚑 {route.vehicleNumber} → Scene
            </span>
          </Tooltip>
        </Polyline>
      )}

      {/* Route label at midpoint of hospital route */}
      {route.routeToHospital.length > 3 && (
        <Polyline
          positions={route.routeToHospital}
          pathOptions={{
            color: '#00d4ff',
            weight: isToHospital ? 4 : 2,
            opacity: hospitalOpacity,
            dashArray: isToHospital ? undefined : '6 8',
          }}
        >
          <Tooltip permanent direction="top" offset={[0, -10]} className="route-label-tooltip">
            <span style={{
              fontFamily: 'monospace', fontSize: '10px', fontWeight: 'bold',
              color: '#00d4ff', background: 'rgba(15,22,41,0.9)',
              padding: '2px 6px', borderRadius: '3px',
              border: '1px solid #00d4ff',
              whiteSpace: 'nowrap',
            }}>
              🚑 {route.vehicleNumber} → {route.hospitalName}
            </span>
          </Tooltip>
        </Polyline>
      )}

      {/* Ambulance current position */}
      <Marker
        position={[route.currentLat, route.currentLon]}
        icon={makeAmbulanceIcon(route.phase, route.heading)}
        zIndexOffset={1000}
      >
        <Tooltip permanent direction="top" offset={[0, -18]} className="ambulance-label-tooltip">
          <span style={{
            fontFamily: 'monospace', fontSize: '10px', fontWeight: 'bold',
            color: '#00d4ff', background: 'rgba(15,22,41,0.9)',
            padding: '2px 6px', borderRadius: '3px',
            border: '1px solid #00d4ff',
            whiteSpace: 'nowrap',
          }}>
            {route.vehicleNumber}
          </span>
        </Tooltip>
        <Popup>
          <div style={{ fontFamily: 'monospace', fontSize: '12px', color: '#e8eaf6', minWidth: '220px' }}>
            <div style={{ fontWeight: 'bold', color: '#00d4ff', marginBottom: '6px' }}>
              🚑 {route.vehicleNumber} ({route.ambulanceType})
            </div>
            <div style={{ marginBottom: '3px' }}>
              <span style={{ color: '#8892b0' }}>Incident:</span> {route.incidentNumber}
            </div>
            <div style={{ marginBottom: '3px' }}>
              <span style={{ color: '#8892b0' }}>Phase:</span>{' '}
              <span style={{ color: route.phase === 'to_hospital' ? '#bf5af2' : '#00d4ff' }}>
                {route.phase === 'to_scene' ? '🔴 En route to scene' :
                 route.phase === 'to_hospital' ? '🔵 Transporting to hospital' :
                 route.phase === 'at_scene' ? '🟡 On scene' : '🟢 At hospital'}
              </span>
            </div>
            <div style={{ marginBottom: '3px' }}>
              <span style={{ color: '#8892b0' }}>ETA:</span>{' '}
              <span style={{ color: '#ff9500', fontWeight: 'bold' }}>{route.etaMinutes.toFixed(0)} min</span>
            </div>
            <div style={{ marginBottom: '3px' }}>
              <span style={{ color: '#8892b0' }}>Speed:</span> {route.speedKmh.toFixed(0)} km/h
            </div>
            <div style={{ marginBottom: '3px' }}>
              <span style={{ color: '#8892b0' }}>Hospital:</span>{' '}
              <span style={{ color: '#30d158' }}>{route.hospitalName}</span>
            </div>
            {route.hospitalSelectionReason && (
              <div style={{
                marginTop: '6px', padding: '4px 6px',
                background: '#0f1629', borderRadius: '4px',
                fontSize: '11px', color: '#8892b0',
                borderLeft: '2px solid #30d158',
              }}>
                {route.hospitalSelectionReason}
              </div>
            )}
            <div style={{ marginTop: '6px' }}>
              <div style={{ color: '#8892b0', fontSize: '10px', marginBottom: '2px' }}>ROUTE PROGRESS</div>
              <div style={{ background: '#1e2d4a', borderRadius: '3px', height: '4px', overflow: 'hidden' }}>
                <div style={{
                  width: `${(route.routeProgress * 100).toFixed(0)}%`,
                  height: '100%',
                  background: '#00d4ff',
                  borderRadius: '3px',
                }} />
              </div>
            </div>
          </div>
        </Popup>
      </Marker>

      {/* Hospital destination marker (highlighted) */}
      {route.hospitalLat && route.hospitalLon && (
        <Marker
          position={[route.hospitalLat, route.hospitalLon]}
          icon={makeHospitalIcon(true)}
          zIndexOffset={900}
        >
          <Popup>
            <div style={{ fontFamily: 'monospace', fontSize: '12px', color: '#e8eaf6', minWidth: '200px' }}>
              <div style={{ fontWeight: 'bold', color: '#30d158', marginBottom: '6px' }}>
                🏥 {route.hospitalName}
              </div>
              <div style={{ marginBottom: '3px', color: '#8892b0', fontSize: '11px' }}>
                Selected for: {route.incidentNumber}
              </div>
              {route.hospitalSelectionReason && (
                <div style={{
                  marginTop: '4px', padding: '4px 6px',
                  background: '#0f1629', borderRadius: '4px',
                  fontSize: '11px', color: '#30d158',
                  borderLeft: '2px solid #30d158',
                }}>
                  ✓ {route.hospitalSelectionReason}
                </div>
              )}
              <div style={{ marginTop: '6px', color: '#00d4ff', fontWeight: 'bold' }}>
                ETA: {route.etaMinutes.toFixed(0)} min
              </div>
            </div>
          </Popup>
        </Marker>
      )}
    </>
  );
}

// ── Map legend ────────────────────────────────────────────────────────────────
function MapLegend() {
  return (
    <div style={{
      position: 'absolute', bottom: '24px', left: '12px', zIndex: 1000,
      background: 'rgba(15,22,41,0.92)', border: '1px solid #1e2d4a',
      borderRadius: '8px', padding: '10px 12px', fontSize: '10px',
      fontFamily: 'monospace', color: '#8892b0', minWidth: '160px',
      backdropFilter: 'blur(8px)',
    }}>
      <div style={{ color: '#e8eaf6', fontWeight: 'bold', marginBottom: '6px', letterSpacing: '0.1em' }}>
        MAP LEGEND
      </div>
      {/* POINT LAYERS */}
      <div style={{ color: '#4a5568', fontSize: '9px', marginTop: '4px', marginBottom: '3px', borderTop: '1px solid #1e2d4a', paddingTop: '4px' }}>
        POINT LAYERS
      </div>
      {[
        { color: '#ff6600', label: 'Accident location', icon: '●' },
        { color: '#00d4ff', label: 'Ambulance (en route)', icon: '◆' },
        { color: '#bf5af2', label: 'Ambulance (transporting)', icon: '◆' },
        { color: '#30d158', label: 'Hospital (selected)', icon: '■' },
        { color: '#1a7a3a', label: 'Hospital (available)', icon: '■' },
      ].map(({ color, label, icon }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
          <div style={{ width: '10px', textAlign: 'center', color, fontSize: '12px', flexShrink: 0 }}>{icon}</div>
          <span>{label}</span>
        </div>
      ))}

      {/* LINE LAYERS */}
      <div style={{ color: '#4a5568', fontSize: '9px', marginTop: '4px', marginBottom: '3px', borderTop: '1px solid #1e2d4a', paddingTop: '4px' }}>
        ROUTE LAYERS
      </div>
      {[
        { color: '#ff2d55', label: 'Ambulance → Scene', dash: false },
        { color: '#00d4ff', label: 'Scene → Hospital', dash: false },
      ].map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
          <div style={{ width: '16px', height: '3px', background: color, borderRadius: '2px', flexShrink: 0 }} />
          <span>{label}</span>
        </div>
      ))}

      {/* RISK LAYERS */}
      <div style={{ color: '#4a5568', fontSize: '9px', marginTop: '4px', marginBottom: '3px', borderTop: '1px solid #1e2d4a', paddingTop: '4px' }}>
        ROAD RISK SEGMENTS
      </div>
      {[
        { color: '#FF0000', label: 'Extreme risk (80-100)' },
        { color: '#FF6600', label: 'High risk (60-80)' },
        { color: '#FFCC00', label: 'Medium risk (40-60)' },
        { color: '#FFFF00', label: 'Low risk (20-40)' },
        { color: '#AAFF00', label: 'Minimal risk (<20)' },
      ].map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
          <div style={{ width: '16px', height: '3px', background: color, borderRadius: '2px', flexShrink: 0 }} />
          <span style={{ fontSize: '9px' }}>{label}</span>
        </div>
      ))}
      <div style={{ marginTop: '6px', fontSize: '9px', color: '#4a5568', borderTop: '1px solid #1e2d4a', paddingTop: '4px' }}>
        💡 Click an incident to focus its route
      </div>
    </div>
  );
}

// ── Interaction hint for focus mode ──────────────────────────────────────────
function FocusHint({ selectedIncidentId }: { selectedIncidentId: string | null }) {
  if (!selectedIncidentId) return null;
  return (
    <div style={{
      position: 'absolute', top: '10px', right: '10px', zIndex: 1000,
      background: 'rgba(15,22,41,0.9)', border: '1px solid #00d4ff',
      borderRadius: '6px', padding: '6px 10px',
      fontFamily: 'monospace', fontSize: '10px', color: '#00d4ff',
      cursor: 'pointer', backdropFilter: 'blur(4px)',
    }}
    onClick={() => useStore.getState().setSelectedIncident(null)}
    title="Click to exit focus mode"
    >
      🔍 FOCUS MODE — Click to exit
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
interface LiveMapProps {
  height?: string;
  showControls?: boolean;
}

export function LiveMap({ height = '100%', showControls = true }: LiveMapProps) {
  const {
    incidents, hospitals, showAmbulances, showHospitals,
    setSelectedIncident, selectedIncidentId, activeRoutes,
  } = useStore();

  const activeIncidents = incidents.filter(
    (i) => i.status !== 'RESOLVED' && i.status !== 'FALSE_ALARM'
  );

  // Hospitals that are currently assigned to an active route
  const assignedHospitalIds = new Set(
    Object.values(activeRoutes).map((r) => r.hospitalId)
  );

  // Determine which routes are "focused" (when an incident is selected)
  const focusedAmbulanceIds = selectedIncidentId
    ? new Set(
        Object.values(activeRoutes)
          .filter((r) => r.incidentId === selectedIncidentId)
          .map((r) => r.ambulanceId)
      )
    : null;

  return (
    <div style={{ height, position: 'relative' }} className="rounded-lg overflow-hidden border border-sos-border">
      <MapContainer
        center={BANGALORE_CENTER}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        zoomControl={showControls}
      >
        {/* Dark CartoDB tiles — no API key needed */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {/* Controllers */}
        <MapController />
        <HeatmapLayer />

        {/* ── Active routes (ambulance + route lines + hospital) ── */}
        {Object.values(activeRoutes).map((route) => {
          const incident = incidents.find((i) => i.id === route.incidentId);
          // In focus mode, only fully show the focused route
          const isFocused = focusedAmbulanceIds
            ? focusedAmbulanceIds.has(route.ambulanceId)
            : true;
          return (
            <RouteOverlay key={route.ambulanceId} route={route} incident={incident} isFocused={isFocused} />
          );
        })}

        {/* ── Incident markers ── */}
        {activeIncidents.map((incident) => {
          const isSelected = selectedIncidentId === incident.id;
          const hasRoute = Object.values(activeRoutes).some((r) => r.incidentId === incident.id);
          // In focus mode, fade non-selected incidents
          const eventListeners = {
            click: () => setSelectedIncident(isSelected ? null : incident.id),
          };
          return (
            <Marker
              key={incident.id}
              position={[incident.latitude, incident.longitude]}
              icon={makeIncidentIcon(incident.severity, isSelected)}
              zIndexOffset={isSelected ? 2000 : (focusedAmbulanceIds && !isSelected ? 100 : 500)}
              opacity={focusedAmbulanceIds && !isSelected ? 0.3 : 1}
              eventHandlers={eventListeners}
            >
              <Popup>
                <IncidentPopup incident={incident} hasRoute={hasRoute} />
              </Popup>
            </Marker>
          );
        })}

        {/* ── Background hospital markers (non-assigned) ── */}
        {showHospitals &&
          hospitals
            .filter((h) => h.latitude && h.longitude && !assignedHospitalIds.has(h.id))
            .slice(0, 15)
            .map((hosp, idx) => (
              <Marker
                key={`${hosp.id}-${idx}`}
                position={[hosp.latitude, hosp.longitude]}
                icon={makeHospitalIcon(false)}
                zIndexOffset={100}
                opacity={focusedAmbulanceIds ? 0.3 : 1}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', fontSize: '12px', color: '#e8eaf6', minWidth: '180px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{hosp.name}</div>
                    <div>Trauma Level: {hosp.trauma_level}</div>
                    <div>
                      ICU: <span style={{ color: '#30d158' }}>{hosp.available_icu_beds}</span>/{hosp.total_icu_beds}
                    </div>
                    <div>
                      Status:{' '}
                      {hosp.is_on_alert
                        ? <span style={{ color: '#ff9500' }}>ON ALERT</span>
                        : <span style={{ color: '#30d158' }}>NORMAL</span>}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
      </MapContainer>

      {/* Overlay info badges */}
      <div style={{
        position: 'absolute', top: '10px', left: '10px', zIndex: 1000,
        display: 'flex', flexDirection: 'column', gap: '4px',
      }}>
        <div style={{
          background: 'rgba(15,22,41,0.9)', border: '1px solid #1e2d4a',
          borderRadius: '6px', padding: '3px 8px', fontSize: '10px',
          fontFamily: 'monospace', color: '#8892b0',
        }}>
          📍 Bangalore, Karnataka
        </div>
        {activeIncidents.length > 0 && (
          <div style={{
            background: 'rgba(255,45,85,0.15)', border: '1px solid rgba(255,45,85,0.4)',
            borderRadius: '6px', padding: '3px 8px', fontSize: '10px',
            fontFamily: 'monospace', color: '#ff2d55',
          }}>
            🔴 {activeIncidents.length} Active Incident{activeIncidents.length !== 1 ? 's' : ''}
          </div>
        )}
        {Object.keys(activeRoutes).length > 0 && (
          <div style={{
            background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
            borderRadius: '6px', padding: '3px 8px', fontSize: '10px',
            fontFamily: 'monospace', color: '#00d4ff',
          }}>
            🚑 {Object.keys(activeRoutes).length} Unit{Object.keys(activeRoutes).length !== 1 ? 's' : ''} Deployed
          </div>
        )}
      </div>

      <FocusHint selectedIncidentId={selectedIncidentId} />
      <MapLegend />
    </div>
  );
}

// ── Incident popup content ────────────────────────────────────────────────────
function IncidentPopup({ incident, hasRoute }: { incident: Incident; hasRoute: boolean }) {
  const color = SEVERITY_COLORS[incident.severity] || '#ff9500';
  return (
    <div style={{ fontFamily: 'monospace', fontSize: '12px', color: '#e8eaf6', minWidth: '240px' }}>
      <div style={{ fontWeight: 'bold', color, marginBottom: '6px', fontSize: '13px' }}>
        {incident.incident_number}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 8px', marginBottom: '6px' }}>
        <div style={{ color: '#8892b0' }}>Severity</div>
        <div style={{ color, fontWeight: 'bold' }}>{incident.severity}</div>
        <div style={{ color: '#8892b0' }}>Status</div>
        <div style={{ color: '#00d4ff' }}>{incident.status.replace(/_/g, ' ')}</div>
        <div style={{ color: '#8892b0' }}>Type</div>
        <div>{incident.event_classification?.replace(/_/g, ' ')}</div>
        {incident.vehicle_type && (
          <>
            <div style={{ color: '#8892b0' }}>Vehicle</div>
            <div>{incident.vehicle_type}</div>
          </>
        )}
        {incident.weather_condition && (
          <>
            <div style={{ color: '#8892b0' }}>Weather</div>
            <div>{incident.weather_condition}</div>
          </>
        )}
      </div>

      <div style={{
        padding: '4px 6px', background: '#0f1629', borderRadius: '4px',
        fontSize: '11px', color: '#8892b0', marginBottom: '6px',
      }}>
        📍 {incident.address}
      </div>

      {/* Ambulance info */}
      {incident.assigned_ambulance_id && (
        <div style={{
          padding: '4px 6px', background: 'rgba(0,212,255,0.08)',
          borderRadius: '4px', borderLeft: '2px solid #00d4ff',
          marginBottom: '4px', fontSize: '11px',
        }}>
          🚑 Ambulance dispatched
          {incident.ambulance_eta_minutes != null && (
            <span style={{ color: '#00d4ff', fontWeight: 'bold' }}>
              {' '}· ETA {incident.ambulance_eta_minutes.toFixed(0)} min
            </span>
          )}
          {incident.ambulance_distance_km != null && (
            <span style={{ color: '#8892b0' }}> ({incident.ambulance_distance_km.toFixed(1)} km)</span>
          )}
        </div>
      )}

      {/* Hospital info */}
      {incident.assigned_hospital_name && (
        <div style={{
          padding: '4px 6px', background: 'rgba(48,209,88,0.08)',
          borderRadius: '4px', borderLeft: '2px solid #30d158',
          marginBottom: '4px', fontSize: '11px',
        }}>
          🏥 {incident.assigned_hospital_name}
          {incident.hospital_eta_minutes != null && (
            <span style={{ color: '#30d158', fontWeight: 'bold' }}>
              {' '}· ETA {incident.hospital_eta_minutes.toFixed(0)} min
            </span>
          )}
        </div>
      )}

      {/* Hospital selection reason */}
      {incident.hospital_selection_reason && (
        <div style={{
          padding: '4px 6px', background: '#0f1629', borderRadius: '4px',
          fontSize: '10px', color: '#30d158', marginBottom: '4px',
          borderLeft: '2px solid #30d158',
        }}>
          ✓ {incident.hospital_selection_reason}
        </div>
      )}

      {/* Route source badge */}
      {incident.route_source && (
        <div style={{ fontSize: '10px', color: '#4a5568', marginTop: '4px' }}>
          Route: {incident.route_source === 'osrm' ? '🗺️ OSRM road-following' : '📏 Straight-line estimate'}
        </div>
      )}

      {/* Confidence */}
      <div style={{ fontSize: '10px', color: '#4a5568', marginTop: '2px' }}>
        Detection confidence: {incident.confidence_level} ·{' '}
        Score: {(incident.crash_probability_score * 100).toFixed(0)}%
      </div>
    </div>
  );
}