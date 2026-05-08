import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Cell
} from 'recharts';
import { useApi } from '../hooks/useApi';
import { useStore } from '../store/useStore';
import { StatCard } from '../components/StatCard';
import {
  TrendingUp, AlertTriangle, Activity, MapPin,
  Download, RefreshCw, Target, Zap
} from 'lucide-react';

export function AdminDashboard() {
  const { blackspots, incidentStats } = useStore();
  const { getTrends, getDistrictStats, getResponseEfficiency, getInfrastructureInsights } = useApi();

  const [trendData, setTrendData] = useState<{ date: string; total_incidents: number; fatal: number; avg_response_time_minutes: number }[]>([]);
  const [districtStats, setDistrictStats] = useState<{ district: string; total_incidents: number; avg_response_time_minutes: number; blackspot_count: number; trend: string }[]>([]);
  const [efficiency, setEfficiency] = useState<{
    avg_detection_to_dispatch_seconds: number;
    avg_dispatch_to_arrival_minutes: number;
    avg_total_response_minutes: number;
    incidents_under_10min_percent: number;
    monthly_trend: { month: string; avg_response_minutes: number; incidents: number }[];
  } | null>(null);
  const [insights, setInsights] = useState<{
    total_segments_requiring_attention: number;
    critical_priority: number;
    estimated_total_cost_crores: number;
    insights: { name: string; risk_score: number; primary_issue: string; recommended_action: string; priority: string }[];
  } | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [trends, districts, eff, infra] = await Promise.all([
        getTrends(selectedDays),
        getDistrictStats(),
        getResponseEfficiency(),
        getInfrastructureInsights(),
      ]);
      if (trends?.daily_data) setTrendData(trends.daily_data);
      if (districts?.districts) setDistrictStats(districts.districts);
      if (eff) setEfficiency(eff);
      if (infra) setInsights(infra);
    } catch {
      // Use mock data
      setTrendData(generateMockTrend(selectedDays));
      setDistrictStats(generateMockDistricts());
      setEfficiency(generateMockEfficiency());
      setInsights(generateMockInsights());
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [selectedDays]);

  const handleExport = () => {
    const data = {
      trends: trendData,
      districts: districtStats,
      efficiency,
      blackspots,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `roadsos-analytics-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full overflow-y-auto bg-sos-bg">
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-bold text-sos-text">Admin Analytics Dashboard</div>
            <div className="text-[11px] text-sos-text-dim">Road Safety Intelligence · Bangalore, Karnataka</div>
          </div>
          <div className="flex items-center gap-2">
            {/* Date range selector */}
            <div className="flex items-center gap-1">
              {[7, 30, 90].map((days) => (
                <button
                  key={days}
                  onClick={() => setSelectedDays(days)}
                  className={`px-2 py-1 rounded text-[10px] font-mono border transition-all ${
                    selectedDays === days
                      ? 'bg-sos-cyan/10 text-sos-cyan border-sos-cyan/30'
                      : 'text-sos-text-muted border-sos-border hover:border-sos-text-dim'
                  }`}
                >
                  {days}D
                </button>
              ))}
            </div>
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-1 px-2 py-1 rounded border border-sos-border text-[10px] text-sos-text-dim hover:border-sos-cyan/30 hover:text-sos-cyan transition-all"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-1 px-2 py-1 rounded border border-sos-border text-[10px] text-sos-text-dim hover:border-sos-green/30 hover:text-sos-green transition-all"
            >
              <Download className="w-3 h-3" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Top Stats */}
        <div className="grid grid-cols-4 gap-3">
          <StatCard
            title="Total Incidents"
            value={trendData.reduce((s, d) => s + d.total_incidents, 0)}
            subtitle={`Last ${selectedDays} days`}
            icon={AlertTriangle}
            color="red"
          />
          <StatCard
            title="Avg Response Time"
            value={efficiency ? `${efficiency.avg_total_response_minutes.toFixed(1)}m` : '—'}
            subtitle="Detection to hospital"
            icon={Activity}
            color="cyan"
          />
          <StatCard
            title="Active Blackspots"
            value={blackspots.length || 0}
            subtitle="Risk score > 70"
            icon={MapPin}
            color="amber"
          />
          <StatCard
            title="Under 10min Response"
            value={efficiency ? `${efficiency.incidents_under_10min_percent.toFixed(0)}%` : '—'}
            subtitle="Response efficiency"
            icon={Target}
            color="green"
          />
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-2 gap-4">
          {/* Accident Trend */}
          <div className="bg-sos-card border border-sos-border rounded-xl p-4">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-3">
              Accident Trend ({selectedDays} Days)
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff2d55" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ff2d55" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="fatalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff9500" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ff9500" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#4a5568' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: '#4a5568' }} width={25} />
                <Tooltip contentStyle={{ background: '#141d35', border: '1px solid #1e2d4a', borderRadius: '8px', color: '#e8eaf6', fontSize: '11px' }} />
                <Area type="monotone" dataKey="total_incidents" stroke="#ff2d55" fill="url(#totalGrad)" strokeWidth={2} name="Total" />
                <Area type="monotone" dataKey="fatal" stroke="#ff9500" fill="url(#fatalGrad)" strokeWidth={1.5} name="Fatal" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Response Efficiency */}
          <div className="bg-sos-card border border-sos-border rounded-xl p-4">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-3">
              Monthly Response Time Trend
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={efficiency?.monthly_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
                <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#4a5568' }} />
                <YAxis tick={{ fontSize: 9, fill: '#4a5568' }} width={25} />
                <Tooltip contentStyle={{ background: '#141d35', border: '1px solid #1e2d4a', borderRadius: '8px', color: '#e8eaf6', fontSize: '11px' }} />
                <Line type="monotone" dataKey="avg_response_minutes" stroke="#00d4ff" strokeWidth={2} dot={{ fill: '#00d4ff', r: 3 }} name="Avg Response (min)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Charts row 2 */}
        <div className="grid grid-cols-3 gap-4">
          {/* District Stats */}
          <div className="col-span-2 bg-sos-card border border-sos-border rounded-xl p-4">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-3">
              District-wise Incidents
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={districtStats.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 9, fill: '#4a5568' }} />
                <YAxis type="category" dataKey="district" tick={{ fontSize: 9, fill: '#8892b0' }} width={100} />
                <Tooltip contentStyle={{ background: '#141d35', border: '1px solid #1e2d4a', borderRadius: '8px', color: '#e8eaf6', fontSize: '11px' }} />
                <Bar dataKey="total_incidents" fill="#ff2d55" radius={[0, 4, 4, 0]} name="Incidents">
                  {districtStats.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={i === 0 ? '#ff2d55' : i === 1 ? '#ff6600' : '#ff9500'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Response Efficiency Metrics */}
          <div className="bg-sos-card border border-sos-border rounded-xl p-4">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest mb-3">
              Response Metrics
            </div>
            {efficiency && (
              <div className="space-y-3">
                {[
                  { label: 'Detection → Dispatch', value: `${efficiency.avg_detection_to_dispatch_seconds.toFixed(0)}s`, color: 'text-sos-green' },
                  { label: 'Dispatch → Arrival', value: `${efficiency.avg_dispatch_to_arrival_minutes.toFixed(1)}m`, color: 'text-sos-cyan' },
                  { label: 'Total Response', value: `${efficiency.avg_total_response_minutes.toFixed(1)}m`, color: 'text-sos-amber' },
                  { label: 'Under 10min', value: `${efficiency.incidents_under_10min_percent.toFixed(0)}%`, color: 'text-sos-green' },
                ].map((metric) => (
                  <div key={metric.label} className="flex items-center justify-between">
                    <span className="text-[11px] text-sos-text-dim">{metric.label}</span>
                    <span className={`text-sm font-mono font-bold ${metric.color}`}>{metric.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Blackspot Analytics */}
        <div className="bg-sos-card border border-sos-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest">
              Top Blackspot Analytics
            </div>
            <div className="text-[10px] text-sos-red font-mono">{blackspots.length} ACTIVE BLACKSPOTS</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-sos-border">
                  {['Location', 'District', 'Risk Score', 'Accidents', 'Primary Factor', 'Trend'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-sos-text-muted font-mono text-[10px] uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(blackspots.length > 0 ? blackspots : generateMockBlackspots()).slice(0, 8).map((spot, i) => (
                  <tr key={i} className="border-b border-sos-border/50 hover:bg-sos-surface/50 transition-colors">
                    <td className="py-1.5 px-2 text-sos-text truncate max-w-[150px]">{spot.name}</td>
                    <td className="py-1.5 px-2 text-sos-text-dim">{spot.district}</td>
                    <td className="py-1.5 px-2">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 bg-sos-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${spot.risk_score}%`,
                              background: spot.risk_score >= 80 ? '#ff2d55' : spot.risk_score >= 60 ? '#ff6600' : '#ff9500'
                            }}
                          />
                        </div>
                        <span className="font-mono text-sos-red">{spot.risk_score.toFixed(0)}</span>
                      </div>
                    </td>
                    <td className="py-1.5 px-2 font-mono text-sos-amber">{spot.total_accidents}</td>
                    <td className="py-1.5 px-2 text-sos-text-dim">{spot.primary_factor}</td>
                    <td className="py-1.5 px-2">
                      <span className={`text-[10px] font-mono ${
                        spot.trend_direction === 'worsening' ? 'text-sos-red' :
                        spot.trend_direction === 'improving' ? 'text-sos-green' :
                        'text-sos-text-dim'
                      }`}>
                        {spot.trend_direction === 'worsening' ? '↑ WORSE' :
                         spot.trend_direction === 'improving' ? '↓ BETTER' : '→ STABLE'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Infrastructure Insights */}
        {insights && (
          <div className="bg-sos-card border border-sos-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] font-mono text-sos-text-dim uppercase tracking-widest flex items-center gap-1.5">
                <Zap className="w-3 h-3 text-sos-amber" />
                Infrastructure Insights
              </div>
              <div className="text-[10px] text-sos-amber font-mono">
                Est. Cost: ₹{insights.estimated_total_cost_crores} Cr
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {insights.insights.slice(0, 6).map((insight, i) => (
                <div key={i} className={`p-2 rounded-lg border ${
                  insight.priority === 'CRITICAL' ? 'bg-sos-red/5 border-sos-red/20' : 'bg-sos-amber/5 border-sos-amber/20'
                }`}>
                  <div className="flex items-start justify-between gap-1">
                    <div className="text-[11px] font-medium text-sos-text truncate">{insight.name}</div>
                    <span className={`text-[9px] font-mono flex-shrink-0 ${
                      insight.priority === 'CRITICAL' ? 'text-sos-red' : 'text-sos-amber'
                    }`}>{insight.priority}</span>
                  </div>
                  <div className="text-[10px] text-sos-text-dim mt-0.5">{insight.primary_issue}</div>
                  <div className="text-[10px] text-sos-cyan mt-0.5">{insight.recommended_action}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Mock data generators for when API is unavailable
function generateMockTrend(days: number) {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (days - i));
    return {
      date: date.toISOString().slice(0, 10),
      total_incidents: Math.floor(Math.random() * 15 + 5),
      fatal: Math.floor(Math.random() * 3),
      avg_response_time_minutes: Math.random() * 6 + 7,
    };
  });
}

function generateMockDistricts() {
  return [
    { district: 'Mahadevapura', total_incidents: 187, avg_response_time_minutes: 9.2, blackspot_count: 6, trend: 'worsening' },
    { district: 'Bommanahalli', total_incidents: 162, avg_response_time_minutes: 10.1, blackspot_count: 5, trend: 'stable' },
    { district: 'Yelahanka', total_incidents: 134, avg_response_time_minutes: 11.3, blackspot_count: 4, trend: 'improving' },
    { district: 'Dasarahalli', total_incidents: 98, avg_response_time_minutes: 12.0, blackspot_count: 3, trend: 'stable' },
    { district: 'Shivajinagar', total_incidents: 87, avg_response_time_minutes: 8.5, blackspot_count: 2, trend: 'improving' },
    { district: 'Rajarajeshwari Nagar', total_incidents: 76, avg_response_time_minutes: 13.2, blackspot_count: 3, trend: 'worsening' },
  ];
}

function generateMockEfficiency() {
  return {
    avg_detection_to_dispatch_seconds: 11.3,
    avg_dispatch_to_arrival_minutes: 8.7,
    avg_total_response_minutes: 11.2,
    incidents_under_10min_percent: 71.4,
    monthly_trend: Array.from({ length: 6 }, (_, i) => {
      const date = new Date();
      date.setMonth(date.getMonth() - (5 - i));
      return {
        month: date.toLocaleString('default', { month: 'short', year: '2-digit' }),
        avg_response_minutes: Math.random() * 4 + 9,
        incidents: Math.floor(Math.random() * 80 + 180),
      };
    }),
  };
}

function generateMockInsights() {
  return {
    total_segments_requiring_attention: 23,
    critical_priority: 8,
    estimated_total_cost_crores: 12.4,
    insights: [
      { name: 'Silk Board Junction', risk_score: 91, primary_issue: 'High accident history', recommended_action: 'Install speed cameras', priority: 'CRITICAL' },
      { name: 'Marathahalli Bridge', risk_score: 87, primary_issue: 'Poor road surface', recommended_action: 'Road resurfacing', priority: 'CRITICAL' },
      { name: 'KR Puram Bridge', risk_score: 83, primary_issue: 'Sharp curves', recommended_action: 'Install guardrails', priority: 'HIGH' },
      { name: 'Hebbal Flyover', risk_score: 79, primary_issue: 'Inadequate lighting', recommended_action: 'Install LED lights', priority: 'HIGH' },
      { name: 'Bannerghatta Road', risk_score: 76, primary_issue: 'High pothole density', recommended_action: 'Emergency patching', priority: 'HIGH' },
      { name: 'Electronic City Flyover', risk_score: 73, primary_issue: 'Traffic management', recommended_action: 'Signal optimization', priority: 'HIGH' },
    ],
  };
}

function generateMockBlackspots() {
  return [
    { name: 'Silk Board Junction', district: 'Bommanahalli', risk_score: 91.2, total_accidents: 47, primary_factor: 'High accident history', trend_direction: 'worsening' },
    { name: 'Marathahalli Bridge', district: 'Mahadevapura', risk_score: 87.5, total_accidents: 38, primary_factor: 'Poor road surface', trend_direction: 'stable' },
    { name: 'KR Puram Bridge', district: 'Mahadevapura', risk_score: 83.1, total_accidents: 31, primary_factor: 'Sharp curves', trend_direction: 'worsening' },
    { name: 'Hebbal Flyover', district: 'Yelahanka', risk_score: 79.8, total_accidents: 28, primary_factor: 'Poor lighting', trend_direction: 'improving' },
    { name: 'Bannerghatta Road', district: 'Bommanahalli', risk_score: 76.3, total_accidents: 24, primary_factor: 'High pothole density', trend_direction: 'stable' },
    { name: 'Outer Ring Road', district: 'Mahadevapura', risk_score: 74.1, total_accidents: 22, primary_factor: 'High traffic density', trend_direction: 'worsening' },
    { name: 'Hosur Road', district: 'Bommanahalli', risk_score: 72.6, total_accidents: 19, primary_factor: 'High accident history', trend_direction: 'stable' },
    { name: 'Tumkur Road', district: 'Dasarahalli', risk_score: 71.0, total_accidents: 17, primary_factor: 'Poor road surface', trend_direction: 'improving' },
  ];
}
