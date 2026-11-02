import { Link } from 'react-router-dom';
import { ArrowRight, GitBranch, Layers3, Search, SlidersHorizontal } from 'lucide-react';
import './About.css';

const workflow = [
  'Submit a Git repository URL.',
  'The backend clones the repository and records its checked-out commit.',
  'Java source files are discovered and parsed; parser and analysis failures are retained as diagnostics.',
  'Twelve static code metrics are extracted from each supported primary file-level class.',
  'Git history is mined for code churn, revision count and developer count.',
  'The scanner assembles the ordered 15-feature vector for each file-level result.',
  'Training-time feature medians fill missing values, then the saved StandardScaler transforms the vector.',
  'Combined Logistic Regression produces a score for the positive (defective) class.',
  'Files are sorted by model score; additional and nested classes are not scored independently.',
  'The dashboard presents the repository summary, diagnostics, ranked files and extracted metrics.',
];

const staticFeatures = ['LOC', 'WMC', 'DIT', 'NOC', 'RFC', 'LCOM5', 'CBO', 'NPA', 'NPM', 'NLE', 'CBOI', 'CD'];
const evolutionFeatures = ['code_churn', 'revision_count', 'developer_count'];

const About = () => (
  <main className="research-page">
    <header className="research-header">
      <p className="eyebrow">Research workflow</p>
      <h1>How repository analysis works</h1>
      <p className="text-muted">
        SQAM combines source-level structure and repository history to estimate which Java files
        may merit earlier manual inspection.
      </p>
    </header>

    <section className="workflow-grid" aria-label="Repository scanning workflow">
      {workflow.map((step, index) => (
        <article className="glass-panel workflow-step" key={step}>
          <span className="workflow-index">{String(index + 1).padStart(2, '0')}</span>
          <p>{step}</p>
        </article>
      ))}
    </section>

    <section className="grid-2 research-section">
      <article className="glass-panel">
        <div className="section-title">
          <Layers3 aria-hidden="true" />
          <h2>Feature configurations</h2>
        </div>
        <p className="text-muted">
          Static-only models use the 12 source metrics. Combined models use all 12 static and all
          3 Git evolution metrics. Repository scans and the deployed model use all 15 features.
        </p>
        <h3>Static code metrics</h3>
        <p className="feature-list">{staticFeatures.join(' · ')}</p>
        <h3>Git evolution metrics</h3>
        <p className="feature-list">{evolutionFeatures.join(' · ')}</p>
        <p className="text-muted">
          The API preserves this ordered 15-feature schema; the manual input page is not part of
          the primary workflow.
        </p>
      </article>

      <article className="glass-panel">
        <div className="section-title">
          <GitBranch aria-hidden="true" />
          <h2>Models and selection</h2>
        </div>
        <p className="text-muted">
          Three classifier families were evaluated with each feature configuration: Logistic
          Regression, Decision Tree and Random Forest. That yields six experimental configurations.
        </p>
        <p className="text-muted">
          Combined Logistic Regression was selected for deployment based on the recorded
          experimental ranking metrics. It is the model loaded for repository scans. This is a
          model-selection result, not evidence that predictions are calibrated or that detected
          files contain defects.
        </p>
        <div className="method-note">
          <strong>Preprocessing is shared with training.</strong>
          <span>Missing values use saved training medians; the saved StandardScaler is applied in the recorded feature order.</span>
        </div>
      </article>
    </section>

    <section className="grid-2 research-section">
      <article className="glass-panel">
        <div className="section-title">
          <SlidersHorizontal aria-hidden="true" />
          <h2>Evaluation methodology</h2>
        </div>
        <p className="text-muted">
          The reported holdout is release-based and chronological: training and test rows are
          separated by release, and preprocessing is fitted on training data. Average Precision is
          the primary precision-recall ranking metric; ROC-AUC, precision, recall, F1 and confusion
          matrices are also reported. See Analytics for the recorded values and curves.
        </p>
        <p className="text-muted">
          The deployed model’s held-out test contains 2,572 components, including 25 labeled
          defective components. The class imbalance makes accuracy alone unsuitable as a measure
          of defect detection.
        </p>
      </article>

      <article className="glass-panel">
        <div className="section-title">
          <Search aria-hidden="true" />
          <h2>Interpreting scan results</h2>
        </div>
        <p className="text-muted">
          Each result represents one primary class/file-level analysis. Additional or nested
          declarations are not given independent predictions. Diagnostics identify parser failures,
          files without resolved identities and unresolved project references.
        </p>
        <p className="score-disclaimer">
          These scores represent the model&apos;s estimates based on source-code metrics and Git
          history. They help prioritize manual inspection and do not confirm the presence of defects.
        </p>
      </article>
    </section>

    <div className="research-cta">
      <Link to="/scanner" className="btn-primary scan-cta">
        <Search size={18} /> Scan a repository <ArrowRight size={18} />
      </Link>
    </div>
  </main>
);

export default About;
