import { useEffect, useState } from 'react';
import { analyticsAPI } from '../api';
import { AlertTriangle } from 'lucide-react';

export default function CarbonPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.dashboard().then(r => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading...</div>;
  if (!data) return null;

  const { emissions } = data;

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Carbon Emissions</h1>
      <div className="card" style={{ border: '1px solid #fde68a', background: '#fffbeb', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <AlertTriangle size={18} color="#d97706" style={{ flexShrink: 0 }} />
          <div>
            <p style={{ fontWeight: 600, color: '#92400e', margin: 0 }}>Important Disclaimer</p>
            <p style={{ fontSize: '0.82rem', color: '#78350f', marginTop: '0.25rem' }}>{emissions?.disclaimer}</p>
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          ['Electricity Consumed', `${emissions?.electricity_kwh?.toLocaleString()} kWh`],
          ['CO₂ Equivalent', `${emissions?.kg_co2e?.toLocaleString()} kgCO₂e`],
          ['In Tonnes', `${emissions?.t_co2e} tCO₂e`],
        ].map(([label, value]) => (
          <div key={label} className="card">
            <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: 0 }}>{label}</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0.25rem 0 0' }}>{value}</p>
          </div>
        ))}
      </div>
      <div className="card">
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Emission Factor Details</h2>
        <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
          <div><dt style={{ color: '#6b7280', fontSize: '0.72rem' }}>Factor Value</dt><dd style={{ fontWeight: 500 }}>{emissions?.emission_factor} {emissions?.unit}/kWh</dd></div>
          <div><dt style={{ color: '#6b7280', fontSize: '0.72rem' }}>Source</dt><dd style={{ fontWeight: 500 }}>{emissions?.emission_factor_source}</dd></div>
          <div style={{ gridColumn: '1/-1' }}><dt style={{ color: '#6b7280', fontSize: '0.72rem' }}>Methodology</dt><dd>Scope 2 (Market-Based) — Grid Electricity × CEA India Emission Factor</dd></div>
        </dl>
      </div>
    </div>
  );
}
