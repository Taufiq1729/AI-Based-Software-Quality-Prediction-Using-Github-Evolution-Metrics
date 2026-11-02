import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import './Analytics.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const MODEL_NAMES = {
  LogisticRegression: 'Logistic Regression',
  DecisionTree: 'Decision Tree',
  RandomForest: 'Random Forest',
};
const MODEL_COLORS = {
  LogisticRegression: '#a78bfa',
  DecisionTree: '#fb923c',
  RandomForest: '#34d399',
};
const VARIANTS = [
  { key: 'static', label: 'Static only' },
  { key: 'combined', label: 'Combined' },
];

const formatMetric = (value) => (
  Number.isFinite(Number(value)) ? Number(value).toFixed(4) : '—'
);

const CurvePlot = ({ title, xLabel, yLabel, curves, xKey, yKey, baseline }) => {
  const toPoints = (curve) => {
    const xs = curve?.[xKey] || [];
    const ys = curve?.[yKey] || [];
    return xs.flatMap((x, index) => (
      Number.isFinite(Number(x)) && Number.isFinite(Number(ys[index]))
        ? [`${40 + Number(x) * 340},${220 - Number(ys[index]) * 190}`]
        : []
    )).join(' ');
  };

  if (!curves.length) return null;

  return (
    <article className="glass-panel curve-panel">
      <h3>{title}</h3>
      <div className="curve-chart">
        <svg viewBox="0 0 400 260" role="img" aria-label={`${title}: ${xLabel} compared with ${yLabel}`}>
          <line x1="40" y1="30" x2="40" y2="220" className="chart-axis" />
          <line x1="40" y1="220" x2="380" y2="220" className="chart-axis" />
          <line x1="40" y1="30" x2="380" y2="30" className="chart-gridline" />
          <line x1="40" y1="125" x2="380" y2="125" className="chart-gridline" />
          <line x1="210" y1="30" x2="210" y2="220" className="chart-gridline" />
          {baseline !== undefined && (
            <line
              x1="40"
              y1={220 - baseline * 190}
              x2="380"
              y2={220 - baseline * 190}
              className="chart-baseline"
            />
          )}
          {title.includes('ROC') && <line x1="40" y1="220" x2="380" y2="30" className="chart-baseline" />}
          {curves.map(({ model, variant, curve }) => (
            <polyline
              key={`${model}-${variant}`}
              points={toPoints(curve)}
              className="curve-line"
              style={{
                stroke: MODEL_COLORS[model],
                strokeDasharray: variant === 'static' ? '5 4' : undefined,
                strokeWidth: model === 'LogisticRegression' && variant === 'combined' ? 3.5 : 2,
                opacity: 0.9,
              }}
            />
          ))}
          <text x="36" y="238" className="chart-tick">0</text>
          <text x="372" y="238" className="chart-tick">1</text>
          <text x="25" y="224" className="chart-tick">0</text>
          <text x="25" y="35" className="chart-tick">1</text>
          <text x="210" y="257" textAnchor="middle" className="chart-label">{xLabel}</text>
          <text x="13" y="125" textAnchor="middle" transform="rotate(-90 13 125)" className="chart-label">{yLabel}</text>
        </svg>
      </div>
      {baseline !== undefined && <p className="chart-footnote">Dashed line: held-out defect prevalence ({(baseline * 100).toFixed(2)}%).</p>}
      {title.includes('ROC') && <p className="chart-footnote">Gray diagonal: no-discrimination reference.</p>}
      <div className="curve-legend">
        {curves.map(({ model, variant }) => (
          <span key={`${model}-${variant}`}>
            <i
              className="legend-line"
              style={{
                backgroundColor: MODEL_COLORS[model],
                borderTop: variant === 'static' ? '2px dashed currentColor' : '2px solid currentColor',
                color: MODEL_COLORS[model],
              }}
            />
            {MODEL_NAMES[model]} · {variant === 'static' ? 'Static' : 'Combined'}
          </span>
        ))}
      </div>
    </article>
  );
};

const CalibrationPlot = ({ bins }) => {
  const points = (bins || []).filter((bin) => (
    Number.isFinite(Number(bin.average_predicted_score))
      && Number.isFinite(Number(bin.observed_defect_fraction))
      && Number(bin.sample_count) > 0
  ));
  if (!points.length) return null;

  return (
    <div className="calibration-chart" aria-label="Reliability diagram for held-out test scores">
      <svg viewBox="0 0 400 260" role="img" aria-label="Average predicted score compared with observed defect fraction">
        <line x1="40" y1="30" x2="40" y2="220" className="chart-axis" />
        <line x1="40" y1="220" x2="380" y2="220" className="chart-axis" />
        <line x1="40" y1="30" x2="380" y2="30" className="chart-gridline" />
        <line x1="40" y1="125" x2="380" y2="125" className="chart-gridline" />
        <line x1="210" y1="30" x2="210" y2="220" className="chart-gridline" />
        <line x1="40" y1="220" x2="380" y2="30" className="chart-baseline" />
        <polyline
          points={points.map((bin) => (
            `${40 + Number(bin.average_predicted_score) * 340},${220 - Number(bin.observed_defect_fraction) * 190}`
          )).join(' ')}
          className="calibration-line"
        />
        {points.map((bin, index) => (
          <circle
            key={bin.probability_interval || index}
            cx={40 + Number(bin.average_predicted_score) * 340}
            cy={220 - Number(bin.observed_defect_fraction) * 190}
            r="4"
            className="calibration-point"
          >
            <title>
              {`${bin.probability_interval}: mean score ${Number(bin.average_predicted_score).toFixed(3)}, observed defect fraction ${Number(bin.observed_defect_fraction).toFixed(3)}, n=${bin.sample_count}`}
            </title>
          </circle>
        ))}
        <text x="36" y="238" className="chart-tick">0</text>
        <text x="372" y="238" className="chart-tick">1</text>
        <text x="25" y="224" className="chart-tick">0</text>
        <text x="25" y="35" className="chart-tick">1</text>
        <text x="210" y="257" textAnchor="middle" className="chart-label">Mean predicted score</text>
        <text x="13" y="125" textAnchor="middle" transform="rotate(-90 13 125)" className="chart-label">Observed defect fraction</text>
      </svg>
      <p className="chart-footnote">Dashed diagonal: perfect calibration. Bins with no samples are omitted.</p>
    </div>
  );
};

const CoefficientChart = ({ coefficients }) => {
  const maximum = Math.max(...coefficients.map((item) => item.magnitude), 0.0001);
  const chartHeight = Math.max(300, coefficients.length * 26 + 20);
  const barStart = 124;
  const barWidth = 340;

  return (
    <div className="coefficient-chart">
      <svg
        viewBox={`0 0 600 ${chartHeight}`}
        role="img"
        aria-label="Absolute standardized coefficient magnitudes for the 15 Combined Logistic Regression features"
      >
        {coefficients.map((item, index) => {
          const y = 18 + index * 26;
          const width = (item.magnitude / maximum) * barWidth;
          const positive = Number(item.Signed_Coefficient) >= 0;
          return (
            <g key={item.Feature}>
              <text x="0" y={y + 10} className="coefficient-feature">{item.Feature}</text>
              <rect
                x={barStart}
                y={y}
                width={width}
                height="12"
                rx="3"
                fill={positive ? '#a78bfa' : '#60a5fa'}
              />
              <text x={barStart + width + 6} y={y + 10} className="coefficient-value">
                {Number(item.Signed_Coefficient).toFixed(3)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="coefficient-legend">
        <span><i className="coefficient-positive" />Positive signed coefficient</span>
        <span><i className="coefficient-negative" />Negative signed coefficient</span>
      </div>
    </div>
  );
};

const ConfusionMatrix = ({ model, variant, metrics }) => {
  const matrix = metrics.ConfusionMatrix;
  if (!Array.isArray(matrix) || matrix.length !== 2) return null;

  return (
    <article className="matrix-card">
      <div className="matrix-heading">
        <strong>{MODEL_NAMES[model]}</strong>
        <span>{variant === 'combined' ? 'Combined' : 'Static only'}</span>
      </div>
      <div className="matrix-axis-label">Predicted</div>
      <div className="matrix-grid" role="table" aria-label={`${MODEL_NAMES[model]} ${variant} confusion matrix`}>
        <span className="matrix-spacer" />
        <span className="matrix-col-label">Non-defect</span>
        <span className="matrix-col-label">Defect</span>
        <span className="matrix-row-label">Non-defect</span>
        <span className="matrix-cell">{formatMetric(matrix[0]?.[0]).replace(/\.0000$/, '')}</span>
        <span className="matrix-cell">{formatMetric(matrix[0]?.[1]).replace(/\.0000$/, '')}</span>
        <span className="matrix-row-label">Defect</span>
        <span className="matrix-cell">{formatMetric(matrix[1]?.[0]).replace(/\.0000$/, '')}</span>
        <span className="matrix-cell">{formatMetric(matrix[1]?.[1]).replace(/\.0000$/, '')}</span>
      </div>
    </article>
  );
};

const Analytics = () => {
  const [metrics, setMetrics] = useState(null);
  const [importance, setImportance] = useState(null);
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [auditError, setAuditError] = useState('');

  useEffect(() => {
    let active = true;

    const fetchResearchData = async () => {
      try {
        const [evaluationResponse, importanceResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/evaluation`),
          axios.get(`${API_BASE_URL}/feature-importance`),
        ]);
        if (!active) return;
        setMetrics(evaluationResponse.data);
        setImportance(importanceResponse.data);

        try {
          const auditResponse = await axios.get(`${API_BASE_URL}/prediction-audit`);
          if (active) setAudit(auditResponse.data);
        } catch {
          if (active) setAuditError('Prediction audit data is unavailable. Model comparison results remain available.');
        }
      } catch {
        if (active) setError('Research results could not be loaded. Confirm the FastAPI backend is running and evaluation artifacts are available.');
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchResearchData();
    return () => { active = false; };
  }, []);

  const modelConfigurations = useMemo(() => (
    Object.keys(MODEL_NAMES).flatMap((model) => VARIANTS.map(({ key, label }) => ({
      model,
      label: MODEL_NAMES[model],
      variant: key,
      featureLabel: label,
      metrics: metrics?.[model]?.[key],
    })).filter((item) => item.metrics))
  ), [metrics]);

  const coefficientData = useMemo(() => (
    [...(importance || [])]
      .sort((left, right) => Number(right.Absolute_Coefficient) - Number(left.Absolute_Coefficient))
      .map((item) => ({
        ...item,
        label: item.Feature,
        magnitude: Number(item.Absolute_Coefficient),
      }))
  ), [importance]);
  const curveSeries = useMemo(() => (
    Object.keys(MODEL_NAMES).flatMap((model) => VARIANTS.map(({ key }) => ({
      model,
      variant: key,
      roc: metrics?.[model]?.[key]?.ROC_Curve,
      pr: metrics?.[model]?.[key]?.PR_Curve,
    })).filter((item) => item.roc && item.pr))
  ), [metrics]);

  if (loading) {
    return <main className="analytics-page"><p className="text-muted" role="status">Loading research results…</p></main>;
  }

  if (error || !metrics) {
    return <main className="analytics-page"><div className="analytics-alert" role="alert">{error || 'Research results are unavailable.'}</div></main>;
  }

  const deployedMetrics = metrics.LogisticRegression?.combined;
  const testMetrics = audit?.held_out_test_metrics;
  const trainingPositiveRate = audit?.model_configuration?.training_positive_fraction;
  const outsideRangeCounts = audit?.scanner_diagnostics?.feature_outside_training_raw_range_count || {};
  const distributionRows = (audit?.scanner_feature_distribution || [])
    .filter((row) => Number(row.scanner_outside_training_range_count) > 0);

  return (
    <main className="analytics-page">
      <header className="analytics-header">
        <p className="eyebrow">Experimental results</p>
        <h1>Model evaluation & validation</h1>
        <p className="text-muted">
          Compare the six recorded model configurations, inspect the deployed model’s evaluation,
          and review limitations in calibration and repository feature coverage.
        </p>
      </header>

      <section className="deployed-banner">
        <span className="deployed-label">Deployed for repository scans</span>
        <strong>Combined Logistic Regression</strong>
        <span>15 extracted features · saved training medians · saved StandardScaler</span>
      </section>

      <section className="analytics-section">
        <div className="section-heading">
          <div>
            <h2>Six model configurations</h2>
            <p className="text-muted">Values are the saved held-out evaluation results; no metrics are recomputed by this dashboard.</p>
          </div>
        </div>
        <div className="metrics-table-wrap">
          <table className="research-table">
            <thead>
              <tr>
                <th>Classifier</th><th>Feature set</th><th>Average Precision</th><th>ROC-AUC</th>
                <th>Precision</th><th>Recall</th><th>F1-score</th>
              </tr>
            </thead>
            <tbody>
              {modelConfigurations.map(({ model, label, variant, featureLabel, metrics: values }) => (
                <tr className={model === 'LogisticRegression' && variant === 'combined' ? 'deployed-row' : ''} key={`${model}-${variant}`}>
                  <td>{label}{model === 'LogisticRegression' && variant === 'combined' && <span className="deployed-inline">Deployed</span>}</td>
                  <td>{featureLabel}</td>
                  <td>{formatMetric(values.Average_Precision)}</td>
                  <td>{formatMetric(values.ROC_AUC)}</td>
                  <td>{formatMetric(values.Precision)}</td>
                  <td>{formatMetric(values.Recall)}</td>
                  <td>{formatMetric(values.F1_Score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="analytics-note">
          Average Precision is the primary precision-recall ranking metric. Trapezoidal PR area is a separate reported value.
          Logistic Regression Combined leads the recorded configurations on Average Precision and ROC-AUC; this does not imply
          reliable probability calibration or external generalization.
        </p>
      </section>

      <section className="curve-grid" aria-label="Classifier evaluation curves">
        <CurvePlot
          title="Precision–recall curves · six configurations"
          xLabel="Recall"
          yLabel="Precision"
          curves={curveSeries.map(({ model, variant, pr }) => ({ model, variant, curve: pr }))}
          xKey="recall"
          yKey="precision"
          baseline={testMetrics?.defect_prevalence}
        />
        <CurvePlot
          title="ROC curves · six configurations"
          xLabel="False positive rate"
          yLabel="True positive rate"
          curves={curveSeries.map(({ model, variant, roc }) => ({ model, variant, curve: roc }))}
          xKey="fpr"
          yKey="tpr"
        />
      </section>

      <section className="analytics-section">
        <div className="section-heading">
          <div>
            <h2>Confusion matrices</h2>
            <p className="text-muted">Rows are actual classes; columns are predicted classes at each model’s recorded default decision rule.</p>
          </div>
        </div>
        <div className="confusion-matrices">
          {modelConfigurations.map(({ model, variant, metrics: values }) => (
            <ConfusionMatrix model={model} variant={variant} metrics={values} key={`matrix-${model}-${variant}`} />
          ))}
        </div>
      </section>

      <section className="grid-2 analytics-section">
        <article className="glass-panel dataset-panel">
          <h2>Held-out dataset</h2>
          <div className="dataset-stats">
            <div><strong>{formatMetric(deployedMetrics?.Sample_Count).replace(/\.0000$/, '')}</strong><span>components in test set</span></div>
            <div><strong>{formatMetric(deployedMetrics?.Defective_Support).replace(/\.0000$/, '')}</strong><span>labeled defective</span></div>
            <div><strong>{formatMetric(deployedMetrics?.NonDefective_Support).replace(/\.0000$/, '')}</strong><span>labeled non-defective</span></div>
            <div><strong>{testMetrics ? `${(testMetrics.defect_prevalence * 100).toFixed(2)}%` : '—'}</strong><span>test defect prevalence</span></div>
          </div>
          <p className="text-muted dataset-note">
            Recorded training positive fraction: {Number.isFinite(trainingPositiveRate) ? `${(trainingPositiveRate * 100).toFixed(2)}%` : 'unavailable'}.
            The held-out labels are strongly imbalanced.
          </p>
        </article>

        <article className="glass-panel calibration-panel">
          <h2>Score calibration and limits</h2>
          {testMetrics ? (
            <>
              <p className="calibration-warning">Scores are uncalibrated model estimates, not verified defect probabilities.</p>
              <dl className="calibration-stats">
                <div><dt>Expected calibration error (10 bins)</dt><dd>{formatMetric(testMetrics.expected_calibration_error_10_equal_width_bins)}</dd></div>
                <div><dt>Brier score</dt><dd>{formatMetric(testMetrics.brier_score)}</dd></div>
                <div><dt>Prevalence-only Brier baseline</dt><dd>{formatMetric(testMetrics.prevalence_only_baseline_brier_score)}</dd></div>
                <div><dt>Calibration model fitted</dt><dd>{testMetrics.calibration_fit_performed ? 'Yes' : 'No'}</dd></div>
              </dl>
              <CalibrationPlot bins={audit?.calibration_bins} />
              <p className="text-muted dataset-note">
                The Brier score is materially worse than the prevalence-only baseline in this test snapshot;
                no calibration model was fitted. The test set contains only 25 positive cases.
              </p>
            </>
          ) : (
            <p className="text-muted">{auditError || 'Calibration audit data is unavailable.'}</p>
          )}
          {audit?.independent_external_repository_labels_available === false && (
            <p className="text-muted dataset-note">No independent defect labels are available for external repository validation.</p>
          )}
          {auditError && <p className="text-muted dataset-note">{auditError}</p>}
        </article>
      </section>

      <section className="grid-2 analytics-section">
        <article className="glass-panel feature-analysis">
          <h2>Feature analysis · deployed model</h2>
          <p className="text-muted">
            Absolute standardized coefficient magnitude for Combined Logistic Regression. The sign indicates
            the fitted direction, not a causal effect.
          </p>
          <p className="text-muted">
            These coefficients are specific to the deployed Logistic Regression model. Legacy generic
            feature-importance and SHAP artifacts describe Random Forest Combined and are not presented as
            Logistic Regression explanations.
          </p>
          {coefficientData.length > 0 ? (
            <CoefficientChart coefficients={coefficientData} />
          ) : (
            <p className="text-muted">{auditError || 'Logistic Regression coefficient data is unavailable.'}</p>
          )}
        </article>

        <article className="glass-panel feature-shift">
          <h2>Repository feature-range checks</h2>
          <p className="text-muted">
            Counts outside the training raw min–max range from a saved Java Design Patterns feature snapshot.
            Its legacy stored scores were generated by Random Forest Combined; the audit recalculated scores
            from those captured features with Logistic Regression Combined. This is not a live scan and has
            no independent defect labels.
          </p>
          {audit?.scanner_diagnostics?.high_score_analysis && (
            <p className="snapshot-summary">
              {formatMetric(audit.scanner_diagnostics.high_score_analysis.captured_repository_feature_rows).replace(/\.0000$/, '')} captured feature rows ·
              {' '}{formatMetric(audit.scanner_diagnostics.high_score_analysis.model_scores_at_least_90_percent).replace(/\.0000$/, '')} LR-recomputed scores ≥ 0.90
            </p>
          )}
          {distributionRows.length > 0 ? (
            <div className="metrics-table-wrap shift-table-wrap">
              <table className="research-table shift-table">
                <thead><tr><th>Feature</th><th>Training range</th><th>Snapshot range</th><th>Outside</th></tr></thead>
                <tbody>
                  {distributionRows.map((row) => (
                    <tr key={row.feature}>
                      <td>{row.feature}</td>
                      <td>{formatMetric(row.training_min)}–{formatMetric(row.training_max)}</td>
                      <td>{formatMetric(row.scanner_min)}–{formatMetric(row.scanner_max)}</td>
                      <td>{formatMetric(outsideRangeCounts[row.feature] ?? row.scanner_outside_training_range_count).replace(/\.0000$/, '')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : audit ? (
            <p className="text-muted">No scanned feature values exceeded the training raw range in this saved snapshot.</p>
          ) : (
            <p className="text-muted">{auditError || 'Repository feature-range audit is unavailable.'}</p>
          )}
          <p className="text-muted dataset-note">
            Distribution differences and high scores are diagnostic signals, not evidence that a file is defective.
          </p>
        </article>
      </section>

      <div className="analytics-disclaimer">
        A high score is not a confirmed defect, nor a calibrated probability. Use results to prioritize manual inspection;
        evaluate external performance only when independent repository labels are available.
      </div>
    </main>
  );
};

export default Analytics;
