import { useState, useEffect } from 'react';
import { actionsAPI, verificationAPI } from '../api';
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const RESULT_ICON = {
  improved:         <CheckCircle size={20} color="#16a34a" />,
  no_change:        <AlertTriangle size={20} color="#d97706" />,
  regressed:        <XCircle size={20} color="#dc2626" />,
  insufficient_data:<AlertTriangle size={20} color="#9ca3af" />,
};

export default function VerificationPage() {
  const [actions, setActions] = useState([]);
  const [selectedAction, setSelectedAction] = useState('');
  const [form, setForm] = useState({
    baseline_start: '', baseline_end: '',
    post_action_start: '', post_action_end: '',
    metric: 'electricity',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    actionsAPI.list().then(r => setActions(r.data));
  }, []);

  const runVerification = async () => {
    if (!selectedAction) { setError('Please select an action.'); return; }
    if (!form.baseline_start || !form.baseline_end || !form.post_action_start || !form.post_action_end) {
      setError('Please fill in all date fields.'); return;
    }
    setLoading(true); setError(''); setResult(null);
    try {
      const r = await verificationAPI.run({ action_id: selectedAction, ...form });
      setResult(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  const fld = (key, label) => (
    <div key={key}>
      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>
        {label}
      </label>
      <input type="date" value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.85rem' }} />
    </div>
  );

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Verification</h1>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>Verify Action Outcome</h2>
        <p style={{ fontSize: '0.82rem', color: '#6b7280', marginBottom: '1rem' }}>
          Requires ≥7 days of post-action data. The system never auto-approves — measured improvement must be shown.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div style={{ gridColumn: '1/-1' }}>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>Select Action</label>
            <select value={selectedAction} onChange={e => setSelectedAction(e.target.value)}
              style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }}>
              <option value="">-- Select an action --</option>
              {actions.map(a => <option key={a.action_id} value={a.action_id}>{a.title?.slice(0, 60)}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>Metric</label>
            <select value={form.metric} onChange={e => setForm(f => ({ ...f, metric: e.target.value }))}
              style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }}>
              <option value="electricity">Electricity (kWh)</option>
              <option value="water">Water (litres)</option>
            </select>
          </div>
          <div />
          {fld('baseline_start', 'Baseline Start')}
          {fld('baseline_end', 'Baseline End')}
          {fld('post_action_start', 'Post-Action Start')}
          {fld('post_action_end', 'Post-Action End')}
        </div>
        <button onClick={runVerification} disabled={loading} className="btn-primary" style={{ marginTop: '1rem' }}>
          {loading ? 'Verifying...' : 'Run Verification'}
        </button>
        {error && <p style={{ color: '#dc2626', fontSize: '0.82rem', marginTop: '0.5rem' }}>{error}</p>}
      </div>

      {result && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            {RESULT_ICON[result.result] || null}
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, textTransform: 'capitalize' }}>
              {result.result?.replace('_', ' ')}
            </h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '0.75rem' }}>
            {[
              ['Baseline Avg', `${result.baseline_value?.toFixed(2)} ${result.metric_unit}`],
              ['Post-Action Avg', `${result.post_action_value?.toFixed(2)} ${result.metric_unit}`],
              ['Change', `${result.measured_change_pct?.toFixed(1)}%`],
              ['Confidence', result.confidence],
            ].map(([label, value]) => (
              <div key={label}>
                <p style={{ fontSize: '0.7rem', color: '#6b7280', margin: 0 }}>{label}</p>
                <p style={{
                  fontSize: '1rem', fontWeight: 700, margin: '0.2rem 0 0',
                  color: label === 'Change' ? (result.measured_change_pct < 0 ? '#16a34a' : '#dc2626') : '#111827'
                }}>{value}</p>
              </div>
            ))}
          </div>
          {result.caveats && (
            <div className="synthetic-banner" style={{ fontSize: '0.78rem' }}>{result.caveats}</div>
          )}
        </div>
      )}
    </div>
  );
}
