import { useEffect, useState } from 'react';
import { auditAPI } from '../api';

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

export default function FindingsPage() {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    auditAPI.list().then(r => {
      setRuns(r.data);
      if (r.data.length > 0) setSelectedRunId(r.data[0].run_id);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    auditAPI.getFindings(selectedRunId).then(r => setFindings(r.data));
  }, [selectedRunId]);

  const sorted = [...findings].sort((a, b) =>
    (SEV_ORDER[a.severity?.toLowerCase()] ?? 5) - (SEV_ORDER[b.severity?.toLowerCase()] ?? 5)
  );

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>Audit Findings</h1>
        {runs.length > 0 && (
          <select value={selectedRunId} onChange={e => setSelectedRunId(e.target.value)}
            style={{ fontSize: '0.82rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.75rem' }}>
            {runs.map(r => <option key={r.run_id} value={r.run_id}>{r.run_id.slice(0, 12)} — {r.created_at?.slice(0, 10)}</option>)}
          </select>
        )}
      </div>

      {loading ? <p style={{ color: '#9ca3af' }}>Loading...</p>
        : sorted.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ color: '#9ca3af' }}>No findings yet. Run an audit first.</p>
          </div>
        ) : sorted.map(f => (
          <div key={f.finding_id} className="card" style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
              <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                <span className={`badge-${f.severity?.toLowerCase() || 'info'}`}>{f.severity?.toUpperCase()}</span>
                <span style={{ fontSize: '0.7rem', background: '#f3f4f6', color: '#6b7280', padding: '0.1rem 0.4rem', borderRadius: '9999px' }}>{f.category}</span>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{f.confidence} conf.</span>
              </div>
              <span style={{ fontSize: '0.72rem', color: '#9ca3af', textTransform: 'capitalize' }}>{f.status}</span>
            </div>
            <h3 style={{ fontSize: '0.88rem', fontWeight: 600, margin: 0 }}>{f.title}</h3>
            <p style={{ fontSize: '0.8rem', color: '#6b7280', margin: '0.25rem 0 0' }}>{f.description}</p>
            {f.metric_value != null && (
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.4rem', fontSize: '0.75rem', color: '#6b7280' }}>
                <span>Value: <strong>{f.metric_value} {f.metric_unit}</strong></span>
                {f.baseline_value && <span>Baseline: <strong>{f.baseline_value}</strong></span>}
                {f.pct_change != null && (
                  <span>Change: <strong style={{ color: f.pct_change > 0 ? '#dc2626' : '#16a34a' }}>
                    {f.pct_change > 0 ? '+' : ''}{f.pct_change?.toFixed(1)}%
                  </strong></span>
                )}
              </div>
            )}
          </div>
        ))
      }
    </div>
  );
}
