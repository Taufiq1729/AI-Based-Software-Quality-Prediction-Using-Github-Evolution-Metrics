import { useState } from 'react';
import axios from 'axios';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import './Predictor.css';

const Predictor = () => {
  const [metrics, setMetrics] = useState({
    WMC: 10, DIT: 2, NOC: 0, CBO: 5, RFC: 15, 
    LCOM5: 0.5, NPA: 0, NPM: 5, NLE: 1, CBOI: 2, 
    CD: 0.1, LOC: 150, 
    code_churn: 100, revision_count: 10, developer_count: 2
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setMetrics(prev => ({ ...prev, [name]: parseFloat(value) }));
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/predict', metrics);
      setResult(response.data);
    } catch (error) {
      console.error("Error predicting:", error);
      alert("Error connecting to backend API.");
    }
    setLoading(false);
  };

  return (
    <div className="predictor-container">
      <div className="glass-panel text-center" style={{ marginBottom: '2rem' }}>
        <h2>SQA Interactive Predictor</h2>
        <p className="text-muted">Simulate a Java component to test its defect probability using our tuned Random Forest Model.</p>
      </div>

      <div className="grid-2">
        <div className="glass-panel">
          <h3 className="text-gradient">📊 Static Metrics</h3>
          
          <div className="input-group">
            <label>Lines of Code (LOC) - {metrics.LOC}</label>
            <input type="range" name="LOC" min="10" max="2000" value={metrics.LOC} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Complexity (WMC) - {metrics.WMC}</label>
            <input type="range" name="WMC" min="1" max="100" value={metrics.WMC} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Coupling (CBO) - {metrics.CBO}</label>
            <input type="range" name="CBO" min="0" max="50" value={metrics.CBO} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Response For Class (RFC) - {metrics.RFC}</label>
            <input type="range" name="RFC" min="0" max="100" value={metrics.RFC} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Lack of Cohesion (LCOM5) - {metrics.LCOM5}</label>
            <input type="range" name="LCOM5" min="0" max="2" step="0.1" value={metrics.LCOM5} onChange={handleChange} />
          </div>
        </div>

        <div>
          <div className="glass-panel" style={{ marginBottom: '2rem' }}>
            <h3 className="text-gradient" style={{ backgroundImage: 'linear-gradient(90deg, #f97316, #ef4444)' }}>📈 Evolution Metrics</h3>
            
            <div className="input-group">
              <label>Code Churn - {metrics.code_churn}</label>
              <input type="range" name="code_churn" min="0" max="5000" value={metrics.code_churn} onChange={handleChange} />
            </div>
            <div className="input-group">
              <label>Revision Count - {metrics.revision_count}</label>
              <input type="range" name="revision_count" min="1" max="200" value={metrics.revision_count} onChange={handleChange} />
            </div>
            <div className="input-group">
              <label>Developer Count - {metrics.developer_count}</label>
              <input type="range" name="developer_count" min="1" max="50" value={metrics.developer_count} onChange={handleChange} />
            </div>
          </div>

          <button className="btn-primary" onClick={handlePredict} disabled={loading} style={{ padding: '1rem', fontSize: '1.2rem' }}>
            {loading ? 'Analyzing...' : '🔍 ANALYZE COMPONENT RISK'}
          </button>

          {result && (
            <div className={`glass-panel result-card ${result.risk_level === 'HIGH' ? 'risk-high' : 'risk-low'}`}>
              {result.risk_level === 'HIGH' ? <AlertTriangle size={48} /> : <CheckCircle2 size={48} />}
              <h2>{result.risk_level} RISK</h2>
              <div className="probability">{(result.probability * 100).toFixed(1)}%</div>
              <p>
                {result.risk_level === 'HIGH' 
                  ? 'This component is highly likely to contain defects. Prioritize for review.' 
                  : 'This component appears stable.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Predictor;
