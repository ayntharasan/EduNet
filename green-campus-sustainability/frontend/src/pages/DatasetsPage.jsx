import { useEffect, useState } from 'react';
import { datasetsAPI } from '../api';
import { Upload, Database, AlertTriangle } from 'lucide-react';

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState({ dataType: 'electricity', name: '', file: null });
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState('');

  const fetch = () => datasetsAPI.list().then(r => setDatasets(r.data)).finally(() => setLoading(false));
  useEffect(() => { fetch(); }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!form.file || !form.name) { setUploadError('Please provide a name and select a file.'); return; }
    setUploading(true); setUploadResult(null); setUploadError('');
    const fd = new FormData();
    fd.append('file', form.file);
    fd.append('name', form.name);
    try {
      const r = await datasetsAPI.upload(form.dataType, fd);
      setUploadResult(r.data);
      fetch();
    } catch (e) {
      setUploadError(e.response?.data?.detail || e.message);
    } finally { setUploading(false); }
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1rem' }}>Dataset Management</h1>

      <div className="synthetic-banner" style={{ display: 'flex', gap: 6, marginBottom: '1rem' }}>
        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>Upload real campus CSV files to replace synthetic demo data. See <code>data/templates/</code> for column format.</span>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Upload New Dataset</h2>
        <form onSubmit={handleUpload}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>Data Type</label>
              <select value={form.dataType} onChange={e => setForm(f => ({ ...f, dataType: e.target.value }))}
                style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }}>
                <option value="electricity">Electricity</option>
                <option value="water">Water</option>
                <option value="waste">Waste</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>Dataset Name</label>
              <input type="text" placeholder="e.g. Main Block Electricity Jan-Jun 2024"
                value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }} />
            </div>
          </div>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: '#6b7280', marginBottom: '0.25rem' }}>CSV or Excel File (max 50MB)</label>
            <input type="file" accept=".csv,.xlsx,.xls"
              onChange={e => setForm(f => ({ ...f, file: e.target.files[0] }))}
              style={{ fontSize: '0.82rem' }} />
          </div>
          <button type="submit" disabled={uploading} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Upload size={14} /> {uploading ? 'Uploading...' : 'Upload'}
          </button>
          {uploadError && <p style={{ color: '#dc2626', fontSize: '0.82rem', marginTop: '0.5rem' }}>{uploadError}</p>}
          {uploadResult && (
            <div style={{ marginTop: '0.75rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '0.5rem', padding: '0.75rem', fontSize: '0.82rem', color: '#15803d' }}>
              <strong>Uploaded!</strong> {uploadResult.rows_imported}/{uploadResult.rows_parsed} rows imported.
              {uploadResult.errors?.length > 0 && <p style={{ color: '#92400e', marginTop: '0.25rem' }}>Warnings: {uploadResult.errors.slice(0, 3).join('; ')}</p>}
            </div>
          )}
        </form>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Registered Datasets</h2>
        {loading ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Loading...</p>
          : datasets.length === 0 ? <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>No datasets registered yet.</p>
          : datasets.map(d => (
            <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.75rem', borderRadius: '0.4rem', background: '#f9fafb', marginBottom: '0.3rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Database size={14} color="#9ca3af" />
                <div>
                  <p style={{ fontSize: '0.82rem', fontWeight: 500, margin: 0 }}>{d.name}</p>
                  <p style={{ fontSize: '0.7rem', color: '#9ca3af', margin: 0 }}>{d.source_type} · {d.row_count} rows · {d.imported_at?.slice(0, 10)}</p>
                </div>
              </div>
              {d.is_synthetic && <span className="badge-medium">SYNTHETIC</span>}
            </div>
          ))
        }
      </div>
    </div>
  );
}
