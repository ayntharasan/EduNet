import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api';
import { AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function WaterPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.water().then(r => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading...</div>;
  if (!data) return null;

  const monthly = (data.monthly_breakdown || []).map(m => ({ month: m.month?.slice(0, 7), litres: m.total_litres }));

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Water Consumption</h1>
      {data.data_source_note?.includes('SYNTHETIC') && (
        <div className="synthetic-banner" style={{ display: 'flex', gap: 6, marginBottom: '1rem' }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} /><span>{data.data_source_note}</span>
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          ['Total', `${data.total_kl?.toLocaleString()} kL`],
          ['Avg Daily', `${data.avg_daily_litres?.toLocaleString()} L`],
          ['Per Person/Day', `${data.litres_per_person_per_day ?? 'N/A'} L`],
          ['Leak Suspects', `${data.leak_suspects?.length ?? 0}`],
        ].map(([label, value]) => (
          <div key={label} className="card">
            <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: 0 }}>{label}</p>
            <p style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0.2rem 0 0' }}>{value}</p>
          </div>
        ))}
      </div>
      {data.leak_suspects?.length > 0 && (
        <div className="card" style={{ border: '1px solid #fed7aa', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#c2410c', marginBottom: '0.5rem' }}>Potential Leak Suspects</h2>
          <p style={{ fontSize: '0.85rem', color: '#4b5563' }}>
            {data.leak_suspects.length} building(s) with suspicious off-hours consumption. Investigate physically.
          </p>
        </div>
      )}
      {monthly.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Monthly Trend</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="litres" fill="#0ea5e9" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
