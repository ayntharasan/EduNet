import { useEffect, useState } from 'react';
import { reportsAPI, auditAPI } from '../api';
import { FileText, Download } from 'lucide-react';

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchReports = () => reportsAPI.list().then(r => setReports(r.data)).finally(() => setLoading(false));

  useEffect(() => {
    fetchReports();
    auditAPI.list().then(r => { setRuns(r.data); if (r.data.length > 0) setSelectedRunId(r.data[0].run_id); });
  }, []);

  const generate = async () => {
    if (!selectedRunId) return;
    setGenerating(true); setMessage('');
    try {
      const r = await reportsAPI.generate(selectedRunId, 'Green Valley University (Demo)');
      setMessage(`Report generated successfully.`);
      fetchReports();
    } catch (e) {
      setMessage(`Error: ${e.response?.data?.detail || e.message}`);
    } finally { setGenerating(false); }
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Reports</h1>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Generate Report</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <select value={selectedRunId} onChange={e => setSelectedRunId(e.target.value)}
            style={{ flex: 1, minWidth: '200px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }}>
            <option value="">-- Select audit run --</option>
            {runs.map(r => <option key={r.run_id} value={r.run_id}>{r.run_id.slice(0, 12)} — {r.created_at?.slice(0, 10)} ({r.findings_count} findings)</option>)}
          </select>
          <button onClick={generate} disabled={generating || !selectedRunId} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <FileText size={14} /> {generating ? 'Generating...' : 'Generate HTML Report'}
          </button>
        </div>
        {message && <p style={{ fontSize: '0.82rem', color: '#4b5563', marginTop: '0.5rem' }}>{message}</p>}
      </div>

      <div className="card">
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Generated Reports</h2>
        {loading ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Loading...</p>
          : reports.length === 0 ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>No reports yet. Generate one above.</p>
          : reports.map(r => (
            <div key={r.report_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.75rem', borderRadius: '0.4rem', background: '#f9fafb', marginBottom: '0.3rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={14} color="#9ca3af" />
                <div>
                  <p style={{ fontSize: '0.82rem', fontWeight: 500, margin: 0 }}>{r.title}</p>
                  <p style={{ fontSize: '0.7rem', color: '#9ca3af', margin: 0 }}>{r.format?.toUpperCase()} · {r.created_at?.slice(0, 16)}</p>
                </div>
              </div>
              <button onClick={() => reportsAPI.download(r.report_id)} className="btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
                <Download size={13} /> Download
              </button>
            </div>
          ))
        }
      </div>
    </div>
  );
}
