import { useEffect, useState } from 'react';
import axios from 'axios';

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({});

  useEffect(() => {
    axios.get('/api/settings')
      .then(r => { setSettings(r.data); setForm({ campus_name: r.data.campus_name, total_students: r.data.total_students || '', total_staff: r.data.total_staff || '' }); })
      .catch(e => setMessage('Error loading settings: ' + e.message))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = { campus_name: form.campus_name };
      if (form.total_students) payload.total_students = parseInt(form.total_students);
      if (form.total_staff) payload.total_staff = parseInt(form.total_staff);
      await axios.patch('/api/settings', payload);
      setMessage('Settings saved successfully.');
    } catch (e) {
      setMessage('Error: ' + (e.response?.data?.detail || e.message));
    } finally { setSaving(false); }
  };

  if (loading) return <div style={{ padding: '2rem', color: '#9ca3af' }}>Loading...</div>;

  const inp = (label, key, type = 'text', placeholder = '') => (
    <div key={key}>
      <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>{label}</label>
      <input type={type} value={form[key] ?? ''} placeholder={placeholder}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.85rem', boxSizing: 'border-box' }} />
    </div>
  );

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Settings</h1>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Campus Configuration</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
          {inp('Campus Name', 'campus_name', 'text', 'e.g. Green Valley University')}
          <div />
          {inp('Total Students', 'total_students', 'number', '1000')}
          {inp('Total Staff', 'total_staff', 'number', '200')}
        </div>
        <button onClick={save} disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save Settings'}</button>
        {message && <p style={{ fontSize: '0.82rem', color: '#4b5563', marginTop: '0.5rem' }}>{message}</p>}
      </div>

      {settings?.emission_factor && (
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Emission Factor (read-only)</h2>
          <dl style={{ fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <dt style={{ color: '#6b7280', width: '5rem' }}>Value:</dt>
              <dd style={{ fontWeight: 500, margin: 0 }}>{settings.emission_factor.value} {settings.emission_factor.unit}</dd>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <dt style={{ color: '#6b7280', width: '5rem' }}>Source:</dt>
              <dd style={{ margin: 0 }}>{settings.emission_factor.source}</dd>
            </div>
          </dl>
          <p style={{ fontSize: '0.72rem', color: '#9ca3af', marginTop: '0.5rem' }}>
            Update DEFAULT_EMISSION_FACTOR in .env and restart the server to change.
          </p>
        </div>
      )}
    </div>
  );
}
