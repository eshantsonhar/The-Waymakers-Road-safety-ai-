import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useStore } from '../store/useStore';
import { useApi } from '../hooks/useApi';
import { LiveMap } from '../components/LiveMap';
import { IncidentFeed } from '../components/IncidentFeed';
import { StatCard } from '../components/StatCard';
import {
  AlertTriangle, Ambulance, Building2, Activity,
  CheckCircle, Layers, Eye, EyeOff, Map
} from 'lucide-react';

const SEVERITY_COLORS = {
  CRITICAL: '#ff2d55',
  HIGH: '#ff6600',
  MEDIUM: '#ff9500',
  LOW: '#30d158',
};

export function CommandCenter() {
  const {
    incidents, ambulances, incidentStats, hospitalStats, ambulanceStats,
    showHeatmap, toggleHeatmap, showAmbulances, toggleAmbulances,
    showHospitals, toggleHospitals,
  } = useStore();
  const { getTrends } = useApi();

  const [trendData, setTrendData] = useState<{ date: string; total_incidents: number; avg_response_time_minutes: number }[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    getTrends(7).then((data) => {
      if (data?.daily_data) setTrendData(data.daily_data.slice(-7));
    }).catch(() => {});
  }, [getTrends]);

  // Global elapsed timer
  useEffect(() => {
    const timer = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const activeIncidents = incidents.filter((i) => i.status !== 'RESOLVED' && i.status !== 'FALSE_ALARM');
  const criticalCount = activeIncidents.filter((i) => i.severity === 'CRITICAL').length;

  // Severity distribution for pie chart
  const severityData = Object.entries(
    activeIncidents.reduce((acc, inc) => {
      acc[inc.severity] = (acc[inc.severity] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({ name, value }));

  // Ambulance status distribution
  const ambStatusData = Object.entries(
    ambulances.reduce((acc, amb) => {
      acc[amb.status] = (acc[amb.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({ name, value }));

  return (
    <div className="h-full flex flex-col bg-sos-bg overflow-hidden">
      {/* Header bar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-2 bg-sos-surface border-b border-sos-border">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${criticalCount > 0 ? 'bg-sos-red animate-pulse' : 'bg-sos-green'}`} />
          <span className="text-xs font-mono text-sos-text-dim">
            COMMAND CENTER
          </span>
        </div>
        <div className="text-xs font-mono text-sos-text-muted">
          {activeIncidents.length} ACTIVE · {ambulances.filter((a) => a.status === 'AVAILABLE').length} AMBULANCES READY
        </div>
        <div className="flex-1" />

        {/* Map layer toggles */}
        <div className="flex items-center gap-1">
          <button
            onClick={toggleHeatmap}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono border transition-all ${
              showHeatmap ? 'bg-sos-amber/10 text-sos-amber border-sos-amber/30' : 'text-sos-text-muted border-sos-border hover:border-sos-text-dim'
            }`}
          >
            <Map className="w-3 h-3" />
            HEATMAP
          </button>
          <button
            onClick={toggleAmbulances}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono border transition-all ${
              showAmbulances ? 'bg-sos-cyan/10 text-sos-cyan border-sos-cyan/30' : 'text-sos-text-muted border-sos-border hover:border-sos-text-dim'
            }`}
          >
            <Ambulance className="w-3 h-3" />
            UNITS
          </button>
          <button
            onClick={toggleHospitals}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono border transition-all ${
              showHospitals ? 'bg-sos-green/10 text-sos-green border-sos-green/30' : 'text-sos-text-muted border-sos-border hover:border-sos-text-dim'
            }`}
          >
            <Building2 className="w-3 h-3" />
            HOSPITALS
          </button>
        </div>
      </div>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden gap-0">
        {/* Left panel - Incident Feed */}
        <div className="w-72 flex-shrink-0 border-r border-sos-border bg-sos-surface flex flex-col overflow-hidden">
          <IncidentFeed />
        </div>

        {/* Center - Map */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Stats row */}
          <div className="flex-shrink-0 grid grid-cols-5 gap-2 p-2 border-b border-sos-border">
            <StatCard
              title="Active Incidents"
              value={activeIncidents.length}
              icon={AlertTriangle}
              color="red"
              animate
            />
            <StatCard
              title="Ambulances Deployed"
              value={ambulanceStats?.deployed ?? ambulances.filter((a) => a.status !== 'AVAILABLE').length}
              icon={Ambulance}
              color="cyan"
              animate
            />
            <StatCard
              title="Hospitals on Alert"
              value={hospitalStats?.on_alert ?? 0}
              icon={Building2}
              color="amber"
              animate
            />
            <StatCard
              title="Avg Response"
              value={`${incidentStats?.avg_response_time_minutes?.toFixed(1) ?? '—'}m`}
              icon={Activity}
              color="green"
            />
            <StatCard
              title="Resolved (24h)"
              value={incidentStats?.resolved_last_24h ?? 0}
              icon={CheckCircle}
              color="purple"
              animate
            />
          </div>

          {/* Map */}
          <div className="flex-1 p-2 overflow-hidden">
            <LiveMap height="100%" />
          </div>
        </div>

        {/* Right panel - Analytics */}
        <div className="w-64 flex-shrink-0 border-l border-sos-border bg-sos-surface flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-sos-border">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-3">
              Severity Distribution
            </div>
            {severityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={120}>
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={30}
                    outerRadius={50}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {severityData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={SEVERITY_COLORS[entry.name as keyof typeof SEVERITY_COLORS] || '#8892b0'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#141d35', border: '1px solid #1e2d4a', borderRadius: '8px', color: '#e8eaf6', fontSize: '11px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-24 flex items-center justify-center text-sos-text-muted text-xs">
                No active incidents
              </div>
            )}
            <div className="flex flex-wrap gap-1 mt-1">
              {Object.entries(SEVERITY_COLORS).map(([sev, color]) => (
                <div key={sev} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                  <span className="text-[9px] text-sos-text-dim">{sev}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Response time trend */}
          <div className="p-3 border-b border-sos-border">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-2">
              7-Day Incident Trend
            </div>
            <ResponsiveContainer width="100%" height={80}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="incidentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#4a5568' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: '#4a5568' }} width={20} />
                <Tooltip
                  contentStyle={{ background: '#141d35', border: '1px solid #1e2d4a', borderRadius: '8px', color: '#e8eaf6', fontSize: '11px' }}
                />
                <Area type="monotone" dataKey="total_incidents" stroke="#00d4ff" fill="url(#incidentGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Ambulance status */}
          <div className="p-3 border-b border-sos-border">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-2">
              Ambulance Status
            </div>
            {ambStatusData.slice(0, 5).map((item) => (
              <div key={item.name} className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] text-sos-text-dim truncate">{item.name.replace(/_/g, ' ')}</span>
                <div className="flex items-center gap-1.5">
                  <div className="w-16 h-1.5 bg-sos-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-sos-cyan rounded-full"
                      style={{ width: `${Math.min(100, (item.value / Math.max(ambulances.length, 1)) * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono text-sos-cyan w-4 text-right">{item.value}</span>
                </div>
              </div>
            ))}
          </div>

          {/* District breakdown */}
          <div className="p-3">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-2">
              District Incidents
            </div>
            {Object.entries(
              activeIncidents.reduce((acc, inc) => {
                const d = inc.district || 'Unknown';
                acc[d] = (acc[d] || 0) + 1;
                return acc;
              }, {} as Record<string, number>)
            )
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([district, count]) => (
                <div key={district} className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-sos-text-dim truncate">{district}</span>
                  <span className="text-[10px] font-mono text-sos-red">{count}</span>
                </div>
              ))}
            {activeIncidents.length === 0 && (
              <div className="text-[10px] text-sos-text-muted">No active incidents</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
