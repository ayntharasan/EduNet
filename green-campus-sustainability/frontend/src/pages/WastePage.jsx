import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api';
import { AlertTriangle } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#22c55e', '#3b82f6', '#f97316', '#8b5cf6'];

export default function WastePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.waste().then(r => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading...</div>;
  if (!data) return null;

  const pie = [
    { name: 'Wet Waste', value: data.total_wet_kg || 0 },
    { name: 'Recyclable', value: data.total_dry_recyclable_kg || 0 },
    { name: 'Residual', value: data.total_residual_kg || 0 },
    { name: 'Special', value: data.total_special_kg || 0 },
  ].filter(d => d.value > 0);

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Waste Management</h1>
      {data.data_source_note?.includes('SYNTHETIC') && (
        <div className="synthetic-banner" style={{ display: 'flex', gap: 6, marginBottom: '1rem' }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} /><span>{data.data_source_note}</span>
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          ['Total Waste', `${data.total_waste_kg?.toLocaleString()} kg`],
          ['Recyclable', `${data.recyclable_fraction_pct ?? '?'}%`],
          ['Residual', `${data.residual_fraction_pct ?? '?'}%`],
          ['Diversion Rate', `${data.diversion_rate_pct ?? '?'}%`],
        ].map(([label, value]) => (
          <div key={label} className="card">
            <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: 0 }}>{label}</p>
            <p style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0.2rem 0 0' }}>{value}</p>
          </div>
        ))}
      </div>
      {pie.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Waste Composition</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={85} label>
                {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
