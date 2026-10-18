import { useEffect, useState } from 'react';
import { actionsAPI, auditAPI } from '../api';

const STATUS_COLORS = {
  draft: { bg: '#f3f4f6', color: '#374151' },
  approved: { bg: '#dbeafe', color: '#1d4ed8' },
  'in-progress': { bg: '#fef9c3', color: '#a16207' },
  completed: { bg: '#dcfce7', color: '#15803d' },
  verified: { bg: '#bbf7d0', color: '#15803d' },
  rejected: { bg: '#fee2e2', color: '#b91c1c' },
};
const VALID_STATUSES = ['draft', 'approved', 'in-progress', 'completed', 'rejected'];

export default function ActionsPage() {
  const [actions, setActions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);

  useEffect(() => {
    auditAPI.list().then(r => {
      setRuns(r.data);
      if (r.data.length > 0) setSelectedRunId(r.data[0].run_id);
    });
  }, []);

  useEffect(() => {
    if (!selectedRunId) { setLoading(false); return; }
    setLoading(true);
    actionsAPI.list({ run_id: selectedRunId }).then(r => setActions(r.data)).finally(() => setLoading(false));
  }, [selectedRunId]);

  const updateStatus = async (actionId, newStatus) => {
    setUpdating(actionId);
    try {
      await actionsAPI.updateStatus(actionId, { new_status: newStatus, changed_by: 'user' });
      const r = await actionsAPI.list({ run_id: selectedRunId });
      setActions(r.data);
    } catch (e) {
      alert(`Error: ${e.response?.data?.detail || e.message}`);
    } finally { setUpdating(null); }
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>Action Plan</h1>
        {runs.length > 0 && (
          <select value={selectedRunId} onChange={e => setSelectedRunId(e.target.value)}
            style={{ fontSize: '0.82rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.75rem' }}>
            {runs.map(r => <option key={r.run_id} value={r.run_id}>{r.run_id.slice(0, 12)} — {r.created_at?.slice(0, 10)}</option>)}
          </select>
        )}
      </div>

      {loading ? <p style={{ color: '#9ca3af' }}>Loading...</p>
        : actions.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ color: '#9ca3af' }}>No actions yet. Run an audit first.</p>
          </div>
        ) : actions.map(a => {
          const sc = STATUS_COLORS[a.status] || STATUS_COLORS.draft;
          return (
            <div key={a.action_id} className="card" style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#16a34a', background: '#f0fdf4', padding: '0.1rem 0.5rem', borderRadius: '9999px' }}>#{a.priority_rank}</span>
                    <span style={{ fontSize: '0.7rem', color: '#6b7280', background: '#f3f4f6', padding: '0.1rem 0.4rem', borderRadius: '9999px' }}>{a.cost_category}</span>
                    <span style={{ fontSize: '0.7rem', color: '#6b7280', background: '#f3f4f6', padding: '0.1rem 0.4rem', borderRadius: '9999px' }}>{a.category}</span>
                    <span style={{ fontSize: '0.7rem', fontWeight: 500, padding: '0.1rem 0.5rem', borderRadius: '9999px', background: sc.bg, color: sc.color }}>{a.status}</span>
                  </div>
                  <h3 style={{ fontSize: '0.88rem', fontWeight: 600, margin: 0 }}>{a.title}</h3>
                  <p style={{ fontSize: '0.8rem', color: '#6b7280', margin: '0.25rem 0 0' }}>{a.description}</p>
                  {a.expected_impact && (
                    <p style={{ fontSize: '0.75rem', color: '#d97706', marginTop: '0.3rem', fontStyle: 'italic' }}>[ESTIMATE] {a.expected_impact}</p>
                  )}
                </div>
                <div style={{ marginLeft: '0.75rem', flexShrink: 0 }}>
                  <select disabled={updating === a.action_id} value={a.status}
                    onChange={e => updateStatus(a.action_id, e.target.value)}
                    style={{ fontSize: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.4rem', padding: '0.3rem 0.5rem' }}>
                    {VALID_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
            </div>
          );
        })
      }
    </div>
  );
}
