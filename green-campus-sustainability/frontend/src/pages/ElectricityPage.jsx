import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api';
import { AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function ElectricityPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analyticsAPI.energy().then(r => setData(r.data)).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading electricity data...</div>;
  if (error) return <div style={{ padding: '2rem', color: '#dc2626' }}>Error: {error}</div>;
  if (!data) return null;

  const monthly = (data.monthly_breakdown || []).map(m => ({ month: m.month?.slice(0, 7), kWh: m.total_kwh }));

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Electricity Consumption</h1>
      {data.data_source_note?.includes('SYNTHETIC') && (
        <div className="synthetic-banner" style={{ display: 'flex', gap: 6, marginBottom: '1rem' }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} /><span>{data.data_source_note}</span>
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          ['Total', `${data.total_kwh?.toLocaleString()} kWh`],
          ['Avg Daily', `${data.avg_daily_kwh} kWh`],
          ['Max Daily', `${data.max_daily_kwh} kWh`],
          ['Per Person', data.kwh_per_person ? `${data.kwh_per_person} kWh` : 'N/A'],
        ].map(([label, value]) => (
          <div key={label} className="card">
            <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: 0 }}>{label}</p>
            <p style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0.2rem 0 0' }}>{value}</p>
          </div>
        ))}
      </div>
      {monthly.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Monthly Trend</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="kWh" fill="#16a34a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {data.emissions && (
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Emissions Estimate</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.72rem', color: '#6b7280' }}>CO₂ Equivalent</p>
              <p style={{ fontSize: '1.2rem', fontWeight: 700 }}>{data.emissions.kg_co2e?.toLocaleString()} kgCO₂e</p>
              <p style={{ fontSize: '0.85rem', color: '#4b5563' }}>{data.emissions.t_co2e} tCO₂e</p>
            </div>
            <div>
              <p style={{ fontSize: '0.72rem', color: '#6b7280' }}>Emission Factor</p>
              <p style={{ fontSize: '0.85rem', fontWeight: 500 }}>{data.emissions.emission_factor} {data.emissions.unit}/kWh</p>
              <p style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{data.emissions.emission_factor_source}</p>
            </div>
          </div>
          <p style={{ fontSize: '0.72rem', color: '#9ca3af', marginTop: '0.75rem', fontStyle: 'italic' }}>{data.emissions.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
