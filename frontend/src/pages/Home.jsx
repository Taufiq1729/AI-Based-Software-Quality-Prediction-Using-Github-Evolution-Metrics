import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, GitCommit, FileCode2 } from 'lucide-react';
import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <div className="hero-section text-center">
        <h1 className="hero-title">
          Empowering SQA with <span className="text-gradient">AI & Git Evolution</span>
        </h1>
        <p className="hero-subtitle text-muted">
          Predict software component defect-proneness by combining static code complexity metrics 
          with historical Git repository evolution data.
        </p>
        <div className="hero-cta">
          <Link to="/predictor" className="btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', width: 'auto' }}>
            Try the Predictor <ArrowRight size={20} />
          </Link>
          <Link to="/about" className="btn-secondary">
            Learn How It Works
          </Link>
        </div>
      </div>

      <div className="features-grid grid-3">
        <div className="glass-panel feature-card">
          <FileCode2 size={40} className="feature-icon static-icon" />
          <h3>Static Code Analysis</h3>
          <p className="text-muted">Analyzes 12 structural metrics like Lines of Code, Cyclomatic Complexity, and Coupling.</p>
        </div>
        <div className="glass-panel feature-card">
          <GitCommit size={40} className="feature-icon git-icon" />
          <h3>Git Evolution Metrics</h3>
          <p className="text-muted">Tracks how the code changes over time using Code Churn, Revision Count, and Developer Count.</p>
        </div>
        <div className="glass-panel feature-card">
          <ShieldCheck size={40} className="feature-icon ai-icon" />
          <h3>AI-Driven Quality</h3>
          <p className="text-muted">Uses Random Forest models to pinpoint high-risk components for targeted QA and testing.</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
