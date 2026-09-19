import { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, LineChart, Line } from 'recharts';

const Analytics = () => {
  const [metrics, setMetrics] = useState(null);
  const [importance, setImportance] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resMetrics, resImp] = await Promise.all([
          axios.get('http://localhost:8000/evaluation'),
          axios.get('http://localhost:8000/feature-importance')
        ]);
        setMetrics(resMetrics.data);
        setImportance(resImp.data);
      } catch (error) {
        console.error("Error fetching analytics data", error);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return <div className="text-center" style={{paddingTop: '5rem'}}>Loading analytics data...</div>;
  if (!metrics) return <div className="text-center" style={{paddingTop: '5rem'}}>Analytics data not available. Ensure backend is running.</div>;

  // Prepare data for Recharts
  const modelNames = Object.keys(metrics);
  const performanceData = modelNames.map(name => ({
    name,
    'Static AUC': metrics[name].static.ROC_AUC,
    'Combined AUC': metrics[name].combined.ROC_AUC,
  }));

  const rocData = [];
  if (metrics.RandomForest && metrics.RandomForest.combined.ROC_Curve) {
    const fprStatic = metrics.RandomForest.static.ROC_Curve.fpr;
    const tprStatic = metrics.RandomForest.static.ROC_Curve.tpr;
    const fprComb = metrics.RandomForest.combined.ROC_Curve.fpr;
    const tprComb = metrics.RandomForest.combined.ROC_Curve.tpr;

    for (let i = 0; i < Math.max(fprStatic.length, fprComb.length); i++) {
      rocData.push({
        fpr: (fprComb[i] || fprComb[fprComb.length - 1]).toFixed(3),
        tprComb: (tprComb[i] || tprComb[tprComb.length - 1]),
        tprStatic: (tprStatic[i] || tprStatic[tprStatic.length - 1])
      });
    }
  }

  return (
    <div style={{ paddingTop: '2rem' }}>
      <h1 className="text-center" style={{ marginBottom: '3rem' }}>Analytics Dashboard</h1>
      
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        <div className="glass-panel">
          <h3>Model Performance (AUC)</h3>
          <p className="text-muted" style={{ marginBottom: '1rem' }}>Comparing Static vs Static + Evolution</p>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="name" stroke="#cbd5e1" />
                <YAxis stroke="#cbd5e1" domain={[0.5, 1]} />
                <Tooltip contentStyle={{ backgroundColor: '#1e1b4b', border: 'none', borderRadius: '8px' }} />
                <Legend />
                <Bar dataKey="Static AUC" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Combined AUC" fill="#d946ef" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel">
          <h3>Top 10 Feature Importance</h3>
          <p className="text-muted" style={{ marginBottom: '1rem' }}>Random Forest (Combined Model)</p>
          <div style={{ width: '100%', height: 300 }}>
            {importance && (
              <ResponsiveContainer>
                <BarChart data={importance.slice(0, 10).reverse()} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                  <XAxis type="number" stroke="#cbd5e1" />
                  <YAxis dataKey="Feature" type="category" stroke="#cbd5e1" width={100} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e1b4b', border: 'none', borderRadius: '8px' }} />
                  <Bar dataKey="Importance" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {rocData.length > 0 && (
        <div className="glass-panel" style={{ width: '100%', maxWidth: '800px', margin: '0 auto' }}>
          <h3>ROC Curve (Random Forest)</h3>
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
              <LineChart data={rocData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="fpr" type="number" domain={[0, 1]} stroke="#cbd5e1" />
                <YAxis domain={[0, 1]} stroke="#cbd5e1" />
                <Tooltip contentStyle={{ backgroundColor: '#1e1b4b', border: 'none', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="tprComb" name="Static + Evolution" stroke="#d946ef" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="tprStatic" name="Static Only" stroke="#3b82f6" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
