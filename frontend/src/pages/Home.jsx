import { Link } from 'react-router-dom';
import { ArrowRight, GitBranch, FileCode2, ScanSearch } from 'lucide-react';
import './Home.css';

const Home = () => {
  return (
    <div className="home-container">
      <section className="hero-section">
        <p className="eyebrow">Software quality research · Java repositories</p>
        <h1 className="hero-title">
          Understand quality signals across <span className="text-gradient">code and change history</span>
        </h1>
        <p className="hero-subtitle text-muted">
          SQAM analyzes Java source and its Git history, then ranks files with a research-selected
          machine-learning model to help guide manual inspection.
        </p>
        <div className="hero-cta">
          <Link to="/scanner" className="btn-primary scan-cta">
            <ScanSearch size={20} /> Scan a repository <ArrowRight size={18} />
          </Link>
          <Link to="/how-it-works" className="btn-secondary">
            Explore the methodology
          </Link>
        </div>
        <p className="hero-disclaimer text-muted">
          Model-estimated scores prioritize review; they do not confirm defects or represent calibrated probabilities.
        </p>
      </section>

      <div className="features-grid grid-3">
        <div className="glass-panel feature-card">
          <FileCode2 size={40} className="feature-icon static-icon" />
          <h3>12 static metrics</h3>
          <p className="text-muted">Measures Java source structure, complexity, cohesion, inheritance and coupling.</p>
        </div>
        <div className="glass-panel feature-card">
          <GitBranch size={40} className="feature-icon git-icon" />
          <h3>3 evolution metrics</h3>
          <p className="text-muted">Mines code churn, revision count and developer count from repository history.</p>
        </div>
        <div className="glass-panel feature-card">
          <ScanSearch size={40} className="feature-icon ai-icon" />
          <h3>File-level prioritization</h3>
          <p className="text-muted">Applies the selected Combined Logistic Regression model to all 15 extracted features.</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
