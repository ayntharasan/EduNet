import { useState, useEffect } from 'react';
import { auditAPI } from '../api';
import { Play, RefreshCw, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';

const STATUS_ICON = {
  complete:  <CheckCircle size={14} color="#16a34a" />,
  failed:    <XCircle size={14} color="#dc2626" />,
  running:   <RefreshCw size={14} color="#2563eb" className="animate-spin" />,
  pending:   <Clock size={14} color="#9ca3af" />,
};

export default function AuditPage() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [message, setMessage] = useState('');
  const [selectedRun, setSelectedRun] = useState(null);
  const [findings, setFindings] = useState([]);
  const [agents, setAgents] = useState([]);

  const fetchRuns = () => {
    setLoading(true);
    auditAPI.list().then(r => setRuns(r.data)).finally(() => setLoading(false));
  };

  useEffect(() => { fetchRuns(); }, []);

  const startAudit = async () => {
    setStarting(true); setMessage('');
    try {
      await auditAPI.start({ use_demo_data: true, triggered_by: 'user' });
      setMessage('Audit started. Refreshing in 6 seconds...');
      setTimeout(() => { fetchRuns(); setMessage(''); }, 6000);
    } catch (e) {
      setMessage(`Error: ${e.response?.data?.detail || e.message}`);
    } finally { setStarting(false); }
  };

  const selectRun = async (run) => {
    setSelectedRun(run);
    const [f, a] = await Promise.all([auditAPI.getFindings(run.run_id), auditAPI.getAgents(run.run_id)]);
    setFindings(f.data); setAgents(a.data);
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>Sustainability Audit</h1>
          <p style={{ color: '#6b7280', fontSize: '0.85rem', margin: '0.2rem 0 0' }}>7-agent AI pipeline</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={fetchRuns} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={startAudit} disabled={starting} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Play size={14} /> {starting ? 'Starting...' : 'Run Audit'}
          </button>
        </div>
      </div>

      <div className="synthetic-banner" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>Uses demo/synthetic data when no real measurements are uploaded. All synthetic findings are clearly labelled.</span>
      </div>

      {message && <div className="synthetic-banner" style={{ marginBottom: '1rem' }}>{message}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: selectedRun ? '1fr 1fr' : '1fr', gap: '1rem' }}>
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Audit Runs</h2>
          {loading ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Loading...</p>
            : runs.length === 0 ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>No runs yet. Click "Run Audit".</p>
            : runs.map(run => (
              <button key={run.run_id} onClick={() => selectRun(run)}
                style={{
                  width: '100%', textAlign: 'left', padding: '0.6rem 0.75rem',
                  borderRadius: '0.5rem', border: selectedRun?.run_id === run.run_id ? '1px solid #86efac' : '1px solid #f3f4f6',
                  background: selectedRun?.run_id === run.run_id ? '#f0fdf4' : '#f9fafb',
                  cursor: 'pointer', marginBottom: '0.4rem',
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', fontWeight: 600 }}>
                    {STATUS_ICON[run.status] || <Clock size={14} />}
                    {run.run_id.slice(0, 12)}...
                  </span>
                  <span style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{run.created_at?.slice(0, 10)}</span>
                </div>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem', fontSize: '0.72rem', color: '#6b7280' }}>
                  <span>{run.findings_count} findings</span>
                  <span>{run.actions_count} actions</span>
                  <span style={{ textTransform: 'capitalize' }}>{run.status}</span>
                </div>
              </button>
            ))
          }
        </div>

        {selectedRun && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="card">
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Agent Pipeline</h2>
              {agents.map(a => (
                <div key={a.agent_name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.6rem', borderRadius: '0.4rem', background: '#f9fafb', marginBottom: '0.3rem' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', fontWeight: 500 }}>
                    {STATUS_ICON[a.status] || <Clock size={13} />}
                    {a.agent_name}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: '#9ca3af' }}>{a.findings_produced} findings · {a.duration_seconds?.toFixed(2)}s</span>
                </div>
              ))}
            </div>

            <div className="card">
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Findings ({findings.length})</h2>
              <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                {findings.map(f => (
                  <div key={f.finding_id} style={{ padding: '0.6rem', borderRadius: '0.4rem', background: '#f9fafb', border: '1px solid #f3f4f6', marginBottom: '0.4rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                      <span className={`badge-${f.severity?.toLowerCase() || 'info'}`}>{f.severity}</span>
                      <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{f.category}</span>
                    </div>
                    <p style={{ fontSize: '0.82rem', fontWeight: 600, margin: 0 }}>{f.title}</p>
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', margin: '0.2rem 0 0', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{f.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
