const About = () => {
  return (
    <div style={{ paddingTop: '2rem', paddingBottom: '4rem' }}>
      <div className="text-center" style={{ marginBottom: '4rem' }}>
        <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>Methodology & Architecture</h1>
        <p className="text-muted" style={{ maxWidth: '800px', margin: '0 auto', fontSize: '1.2rem', lineHeight: '1.6' }}>
          An empirical approach to Software Quality Assurance (SQA) utilizing Machine Learning and Multi-Dimensional Code Analysis.
        </p>
      </div>
      
      <div className="glass-panel" style={{ marginBottom: '3rem' }}>
        <h2 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>1. Research Objective</h2>
        <p className="text-muted" style={{ lineHeight: '1.8', fontSize: '1.1rem' }}>
          The primary objective of this system is to proactively estimate the quality risk and defect-proneness of software components. 
          By synthesizing <b>Static Object-Oriented Code Metrics</b> with historical <b>Git Evolution Metrics</b>, the platform empowers 
          Quality Assurance (QA) teams and developers to optimize code review allocation and testing resources based on quantitative evidence.
          <br /><br />
          The underlying models are trained and validated on the <i>"Software Metrics for Software Defects Prediction"</i> dataset 
          (DOI: 10.6084/m9.figshare.21150994), ensuring robust performance across diverse Java repositories.
        </p>
      </div>

      <div className="grid-2" style={{ marginBottom: '3rem' }}>
        <div className="glass-panel">
          <h3 style={{ color: '#3b82f6', marginBottom: '1.5rem' }}>2. Static Code Taxonomy</h3>
          <p className="text-muted" style={{ marginBottom: '1.5rem' }}>
            Static metrics are extracted directly from the source code's Abstract Syntax Tree (AST), representing structural complexity and object-oriented design cohesion.
          </p>
          <ul className="text-muted" style={{ lineHeight: '2.2', paddingLeft: '1.5rem' }}>
              <li><b>LOC (Lines of Code)</b>: Volumetric measurement of component size.</li>
              <li><b>WMC (Weighted Methods per Class)</b>: Cyclomatic complexity aggregate.</li>
              <li><b>DIT (Depth of Inheritance Tree)</b>: Maximum path length from the node to the root of the tree.</li>
              <li><b>CBO (Coupling Between Objects)</b>: Number of classes to which a class is coupled.</li>
              <li><b>LCOM5 (Lack of Cohesion in Methods)</b>: Evaluates the relatedness of methods and instance variables.</li>
              <li><b>RFC (Response For a Class)</b>: The set of methods that can potentially be executed in response to a message.</li>
          </ul>
        </div>
        
        <div className="glass-panel">
          <h3 style={{ color: '#d946ef', marginBottom: '1.5rem' }}>3. Git Evolution Taxonomy</h3>
          <p className="text-muted" style={{ marginBottom: '1.5rem' }}>
            Evolution metrics (process metrics) are mined from the Version Control System (VCS), capturing the temporal dynamics and human organizational factors of software development.
          </p>
          <ul className="text-muted" style={{ lineHeight: '2.2', paddingLeft: '1.5rem' }}>
              <li><b>Code Churn</b>: The absolute sum of lines added, deleted, and modified. High churn strongly correlates with architectural instability.</li>
              <li><b>Revision Count</b>: The absolute frequency of historical commits affecting a file, indicating active maintenance or persistent bug fixing.</li>
              <li><b>Developer Count</b>: The cardinality of distinct authors contributing to a file. High developer count often indicates distributed ownership, which can increase defect risk.</li>
          </ul>
        </div>
      </div>

      <div className="glass-panel">
        <h2 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>4. Core Research Questions (RQs)</h2>
        <p className="text-muted" style={{ marginBottom: '1.5rem' }}>
          The architecture of this platform is designed to answer four fundamental research questions regarding software quality prediction:
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <b style={{ color: '#f8fafc', fontSize: '1.1rem' }}>RQ1: Hypothesis Validation</b>
            <p className="text-muted" style={{ marginTop: '0.5rem', margin: 0 }}>Does the integration of evolution/process metrics with static code metrics yield a statistically significant improvement in defect-proneness prediction accuracy?</p>
          </div>
          <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <b style={{ color: '#f8fafc', fontSize: '1.1rem' }}>RQ2: Feature Importance</b>
            <p className="text-muted" style={{ marginTop: '0.5rem', margin: 0 }}>Which individual metrics—structural or temporal—exhibit the highest information gain when classifying defect-prone components?</p>
          </div>
          <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <b style={{ color: '#f8fafc', fontSize: '1.1rem' }}>RQ3: Algorithmic Efficacy</b>
            <p className="text-muted" style={{ marginTop: '0.5rem', margin: 0 }}>Among standard classifiers (Logistic Regression, Decision Trees, Random Forests), which algorithm achieves the optimal balance of Precision, Recall, and Area Under the ROC Curve (AUC)?</p>
          </div>
          <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}>
            <b style={{ color: '#f8fafc', fontSize: '1.1rem' }}>RQ4: Model Explainability</b>
            <p className="text-muted" style={{ marginTop: '0.5rem', margin: 0 }}>To what extent can explainable AI techniques (e.g., SHAP values) provide actionable, human-interpretable insights for QA teams regarding why a specific file was flagged?</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default About;
