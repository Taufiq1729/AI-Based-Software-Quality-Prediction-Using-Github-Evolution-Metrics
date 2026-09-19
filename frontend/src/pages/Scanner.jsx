import { useState } from 'react';
import axios from 'axios';
import { Search, Loader2, ShieldAlert, CheckCircle2 } from 'lucide-react';

const Scanner = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleScan = async (e) => {
    e.preventDefault();
    if (!repoUrl.includes('github.com')) {
      setError("Please enter a valid GitHub repository URL.");
      return;
    }
    
    setLoading(true);
    setError('');
    setResults(null);
    
    try {
      const response = await axios.post('http://localhost:8000/scan-repo', { url: repoUrl });
      setResults(response.data.files);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "An error occurred while scanning the repository.");
    }
    
    setLoading(false);
  };

  return (
    <div style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
      <div className="text-center" style={{ marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>Repository Scanner</h1>
        <p className="text-muted" style={{ maxWidth: '800px', margin: '0 auto', fontSize: '1.2rem', lineHeight: '1.6' }}>
          Input a public GitHub repository. Our AI will analyze the Git evolution history and static code structure to identify the most defect-prone Java files.
        </p>
      </div>

      <div className="glass-panel" style={{ maxWidth: '800px', margin: '0 auto 3rem auto' }}>
        <form onSubmit={handleScan} style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ flex: 1 }}>
            <input 
              type="url" 
              placeholder="https://github.com/user/repository" 
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              required
              style={{
                width: '100%', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(0,0,0,0.2)', color: 'white', fontSize: '1.1rem'
              }}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading} style={{ width: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {loading ? <Loader2 className="animate-spin" /> : <Search />}
            {loading ? 'Scanning...' : 'Scan Repository'}
          </button>
        </form>
        {error && <p style={{ color: '#ef4444', marginTop: '1rem', fontWeight: '500' }}>{error}</p>}
      </div>

      {loading && (
        <div className="text-center text-muted" style={{ padding: '3rem' }}>
          <Loader2 size={48} className="animate-spin" style={{ margin: '0 auto 1rem auto', color: '#8b5cf6' }} />
          <h3>Analyzing Repository...</h3>
          <p>This may take a few minutes depending on the repository size. We are cloning the repository, mining the Git commit history, extracting static metrics, and running the Random Forest inference.</p>
        </div>
      )}

      {results && results.length > 0 && (
        <div className="glass-panel">
          <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert color="#ef4444" /> Highest Risk Files Detected
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                  <th style={{ padding: '1rem', color: '#94a3b8' }}>File Path</th>
                  <th style={{ padding: '1rem', color: '#94a3b8' }}>LOC</th>
                  <th style={{ padding: '1rem', color: '#94a3b8' }}>Code Churn</th>
                  <th style={{ padding: '1rem', color: '#94a3b8' }}>Revisions</th>
                  <th style={{ padding: '1rem', color: '#94a3b8' }}>Defect Risk</th>
                </tr>
              </thead>
              <tbody>
                {results.map((file, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: file.risk_level === 'HIGH' ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}>
                    <td style={{ padding: '1rem', wordBreak: 'break-all' }}>{file.file}</td>
                    <td style={{ padding: '1rem' }}>{file.loc}</td>
                    <td style={{ padding: '1rem' }}>{file.churn}</td>
                    <td style={{ padding: '1rem' }}>{file.revisions}</td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: file.risk_level === 'HIGH' ? '#ef4444' : '#22c55e', fontWeight: 'bold' }}>
                        {file.risk_level === 'HIGH' ? <ShieldAlert size={18} /> : <CheckCircle2 size={18} />}
                        {(file.risk_probability * 100).toFixed(1)}%
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {results && results.length === 0 && (
        <div className="glass-panel text-center">
          <p className="text-muted">No Java files found in this repository.</p>
        </div>
      )}
    </div>
  );
};

export default Scanner;
