import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api';
import { Zap, Droplets, Trash2, Wind, AlertTriangle } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function KPICard({ title, value, unit, icon: Icon, color, note }) {
  const colors = { green: '#16a34a', blue: '#0ea5e9', orange: '#f97316', gray: '#6b7280', yellow: '#d97706' };
  const bg = { green: '#f0fdf4', blue: '#e0f2fe', orange: '#fff7ed', gray: '#f9fafb', yellow: '#fefce8' };
  const c = colors[color] || colors.green;
  const b = bg[color] || bg.green;
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ fontSize: '0.8rem', color: '#6b7280', fontWeight: 500, margin: 0 }}>{title}</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0.25rem 0 0' }}>
            {value ?? '—'} <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#9ca3af' }}>{unit}</span>
          </p>
          {note && <p style={{ fontSize: '0.7rem', color: '#9ca3af', margin: '0.25rem 0 0' }}>{note}</p>}
        </div>
        <div style={{ width: 36, height: 36, borderRadius: '0.5rem', background: b, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={18} color={c} />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analyticsAPI.dashboard()
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading dashboard...</div>;
  if (error) return <div style={{ padding: '2rem', color: '#dc2626' }}>Error: {error}. Is the backend running on port 8000?</div>;
  if (!data) return null;

  const { energy, water, waste, emissions, is_demo_data, demo_warning } = data;
  const monthly = (energy?.monthly_breakdown || []).map(m => ({ month: m.month?.slice(0, 7), kWh: m.total_kwh }));

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>Campus Dashboard</h1>
        <p style={{ color: '#6b7280', fontSize: '0.85rem', margin: '0.2rem 0 0' }}>Real-time sustainability overview</p>
      </div>

      {is_demo_data && (
        <div className="synthetic-banner" style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{demo_warning}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <KPICard title="Total Electricity" value={energy?.total_kwh?.toLocaleString()} unit="kWh" icon={Zap} color="yellow" note={`Avg ${energy?.avg_daily_kwh} kWh/day`} />
        <KPICard title="Total Water" value={water?.total_kl?.toLocaleString()} unit="kL" icon={Droplets} color="blue" note={`Avg ${water?.avg_daily_litres?.toLocaleString()} L/day`} />
        <KPICard title="Total Waste" value={waste?.total_waste_kg?.toLocaleString()} unit="kg" icon={Trash2} color="orange" note={`Recycling: ${waste?.recyclable_fraction_pct ?? '?'}%`} />
        <KPICard title="CO₂ Estimate" value={emissions?.t_co2e?.toLocaleString()} unit="tCO₂e" icon={Wind} color="gray" note="Scope 2 ESTIMATE only" />
      </div>

      {monthly.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Monthly Electricity Consumption</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={monthly}>
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={v => [`${v?.toLocaleString()} kWh`, 'Electricity']} />
              <Area type="monotone" dataKey="kWh" stroke="#16a34a" fill="url(#grad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          {is_demo_data && <p style={{ fontSize: '0.7rem', color: '#d97706', marginTop: '0.5rem' }}>[SYNTHETIC DEMO DATA] Not real campus measurements.</p>}
        </div>
      )}

      {emissions?.disclaimer && (
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>Emissions Disclaimer</h2>
          <p style={{ fontSize: '0.82rem', color: '#4b5563' }}>{emissions.disclaimer}</p>
          <p style={{ fontSize: '0.72rem', color: '#9ca3af', marginTop: '0.3rem' }}>Source: {emissions.emission_factor_source}</p>
        </div>
      )}
    </div>
  );
}
