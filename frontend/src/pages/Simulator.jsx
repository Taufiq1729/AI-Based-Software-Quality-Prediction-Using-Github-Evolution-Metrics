import React, { useState } from 'react';
import axios from 'axios';
import { 
  Sliders, 
  Cpu, 
  ShieldAlert, 
  ShieldCheck, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  RotateCcw, 
  Info,
  Layers,
  FileCode,
  History
} from 'lucide-react';
import { useScan } from '../context/ScanContext';
import MetricTooltip from '../components/MetricTooltip';

const PRESETS = [
  {
    name: 'Stable Domain Entity',
    desc: 'Modest size, minimal branching, stable Git history',
    metrics: {
      LOC: 85, WMC: 6, DIT: 1, NOC: 0, CBO: 3, RFC: 8,
      LCOM5: 0.1, NPA: 0, NPM: 8, NLE: 1, CBOI: 4, CD: 0.22,
      code_churn: 45, revision_count: 3, developer_count: 1
    }
  },
  {
    name: 'Volatile Bug Hotspot',
    desc: 'High historical churn, frequent changes, high coupling',
    metrics: {
      LOC: 650, WMC: 42, DIT: 3, NOC: 2, CBO: 24, RFC: 48,
      LCOM5: 0.85, NPA: 4, NPM: 28, NLE: 5, CBOI: 12, CD: 0.04,
      code_churn: 3200, revision_count: 65, developer_count: 8
    }
  },
  {
    name: 'Legacy God Class',
    desc: 'Massive code size and complexity, but infrequent revisions',
    metrics: {
      LOC: 1200, WMC: 55, DIT: 2, NOC: 0, CBO: 18, RFC: 50,
      LCOM5: 0.90, NPA: 8, NPM: 35, NLE: 4, CBOI: 8, CD: 0.08,
      code_churn: 350, revision_count: 8, developer_count: 2
    }
  }
];

const Simulator = () => {
  const { apiBase, selectedModel, threshold } = useScan();

  const [metrics, setMetrics] = useState({
    LOC: 150, WMC: 12, DIT: 2, NOC: 0, CBO: 8, RFC: 16,
    LCOM5: 0.4, NPA: 0, NPM: 8, NLE: 2, CBOI: 3, CD: 0.12,
    code_churn: 150, revision_count: 12, developer_count: 3
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [simModel, setSimModel] = useState(selectedModel);

  const handleSliderChange = (key, value) => {
    setMetrics(prev => ({ ...prev, [key]: Number(value) }));
  };

  const handleApplyPreset = (preset) => {
    setMetrics({ ...preset.metrics });
    setResult(null);
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${apiBase}/api/predict-component`, {
        ...metrics,
        model_name: simModel,
        threshold: threshold
      });
      setResult(response.data);
    } catch (err) {
      console.error('Error running simulation:', err);
    } finally {
      setLoading(false);
    }
  };

  const pred = result?.prediction;
  const expl = result?.explanation;
  const isHighRisk = pred?.risk_level === 'HIGH';

  return (
    <div className="space-y-8 py-2 max-w-5xl mx-auto">
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 text-xs font-semibold mb-2">
          <Cpu size={13} />
          <span>Interactive Component Simulator</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Component Defect Risk Simulator
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Simulate hypothetical or planned Java components to estimate their defect risk prior to commit.
        </p>
      </div>

      {/* Preset Archetypes */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-4">
        <span className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider block mb-2">
          Load Architectural Archetype Preset:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => handleApplyPreset(p)}
              className="p-3 text-left rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/30 border border-slate-200 dark:border-slate-700/60 transition group"
            >
              <span className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 block">
                {p.name}
              </span>
              <span className="text-[11px] text-slate-600 dark:text-slate-300 block mt-0.5">
                {p.desc}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Sliders Grid: Static (12) + Evolution (3) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Metric Sliders (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* 3 Git Evolution Metrics Sliders */}
          <div className="bg-white dark:bg-slate-900 border border-purple-200 dark:border-purple-900/50 rounded-2xl shadow-subtle p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-purple-700 dark:text-purple-300 flex items-center gap-2">
              <History size={15} />
              <span>Git Evolution Metrics (Primary Volatility Drivers)</span>
            </h3>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <MetricTooltip metricKey="code_churn">
                    <span className="text-slate-800 dark:text-slate-200 font-semibold">Code Churn</span>
                  </MetricTooltip>
                  <span className="font-mono font-bold text-purple-600 dark:text-purple-400">{metrics.code_churn} lines</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="5000"
                  step="50"
                  value={metrics.code_churn}
                  onChange={(e) => handleSliderChange('code_churn', e.target.value)}
                  className="w-full accent-purple-600 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <MetricTooltip metricKey="revision_count">
                    <span className="text-slate-800 dark:text-slate-200 font-semibold">Revision Count</span>
                  </MetricTooltip>
                  <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">{metrics.revision_count} commits</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="150"
                  step="1"
                  value={metrics.revision_count}
                  onChange={(e) => handleSliderChange('revision_count', e.target.value)}
                  className="w-full accent-indigo-600 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <MetricTooltip metricKey="developer_count">
                    <span className="text-slate-800 dark:text-slate-200 font-semibold">Developer Count</span>
                  </MetricTooltip>
                  <span className="font-mono font-bold text-blue-600 dark:text-blue-400">{metrics.developer_count} authors</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  step="1"
                  value={metrics.developer_count}
                  onChange={(e) => handleSliderChange('developer_count', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* 12 Static OO Metrics Sliders */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <FileCode size={15} className="text-blue-600" />
              <span>Static Object-Oriented Metrics</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="LOC"><span>Lines of Code (LOC)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.LOC}</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="2000"
                  step="10"
                  value={metrics.LOC}
                  onChange={(e) => handleSliderChange('LOC', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="WMC"><span>Complexity (WMC)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.WMC}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="80"
                  value={metrics.WMC}
                  onChange={(e) => handleSliderChange('WMC', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="CBO"><span>Coupling (CBO)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.CBO}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="40"
                  value={metrics.CBO}
                  onChange={(e) => handleSliderChange('CBO', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="RFC"><span>Response (RFC)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.RFC}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="80"
                  value={metrics.RFC}
                  onChange={(e) => handleSliderChange('RFC', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="LCOM5"><span>Cohesion Lack (LCOM5)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.LCOM5}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.05"
                  value={metrics.LCOM5}
                  onChange={(e) => handleSliderChange('LCOM5', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="NLE"><span>Max Nesting (NLE)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.NLE}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="8"
                  value={metrics.NLE}
                  onChange={(e) => handleSliderChange('NLE', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="DIT"><span>Inheritance Depth (DIT)</span></MetricTooltip>
                  <span className="font-mono font-bold">{metrics.DIT}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="6"
                  value={metrics.DIT}
                  onChange={(e) => handleSliderChange('DIT', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <MetricTooltip metricKey="CD"><span>Comment Density (CD)</span></MetricTooltip>
                  <span className="font-mono font-bold">{(metrics.CD * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.02"
                  value={metrics.CD}
                  onChange={(e) => handleSliderChange('CD', e.target.value)}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Model selector & Predict Trigger */}
          <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle flex flex-col sm:flex-row items-center gap-4">
            <div className="flex-1 w-full">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Prediction Model Configuration
              </label>
              <select
                value={simModel}
                onChange={(e) => setSimModel(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200"
              >
                <option value="LogisticRegression_combined">Logistic Regression (Combined) ★ Primary</option>
                <option value="LogisticRegression_static">Logistic Regression (Static Only)</option>
                <option value="RandomForest_combined">Random Forest (Combined)</option>
                <option value="RandomForest_static">Random Forest (Static Only)</option>
                <option value="DecisionTree_combined">Decision Tree (Combined)</option>
                <option value="DecisionTree_static">Decision Tree (Static Only)</option>
              </select>
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={loading}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/25 transition disabled:opacity-50 shrink-0"
            >
              {loading ? 'Evaluating...' : 'Run Prediction'}
            </button>
          </div>
        </div>

        {/* Right Column: Prediction & SHAP Output (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {pred ? (
            <div className={`p-6 rounded-2xl border ${
              isHighRisk 
                ? 'bg-red-50/40 border-red-200 dark:bg-red-950/20 dark:border-red-900/60' 
                : 'bg-emerald-50/40 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/60'
            } shadow-subtle space-y-4`}>
              <div className="text-center space-y-1">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                  isHighRisk 
                    ? 'bg-red-100 text-red-700 dark:bg-red-950/80 dark:text-red-300 border border-red-200 dark:border-red-800' 
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                }`}>
                  {isHighRisk ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
                  <span>{pred.risk_level} RISK</span>
                </span>

                <div className="pt-2">
                  <span className="text-4xl font-extrabold text-slate-900 dark:text-white font-mono">
                    {(pred.risk_score * 100).toFixed(1)}%
                  </span>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                    Predicted Relative Defect-Risk Probability
                  </p>
                </div>
              </div>

              {/* Natural Language Diagnostic */}
              <div className="p-3.5 bg-white/80 dark:bg-slate-900/80 rounded-xl border border-slate-200/80 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 space-y-1">
                <span className="font-bold flex items-center gap-1.5 text-slate-900 dark:text-white">
                  <Sparkles size={14} className="text-blue-500" />
                  <span>AI Diagnostic Summary:</span>
                </span>
                <p className="leading-relaxed">
                  {expl?.narrative_explanation || pred.explanation_summary}
                </p>
              </div>

              {/* Top SHAP Drivers */}
              {expl?.top_drivers && (
                <div className="space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block">
                    Key Metric Risk Influencers:
                  </span>
                  {expl.top_drivers.slice(0, 4).map((d, idx) => {
                    const isPos = d.shap_value > 0;
                    return (
                      <div key={idx} className="p-2.5 rounded-lg bg-white/60 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800 flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-800 dark:text-slate-200">{d.label}</span>
                        <span className={`font-mono font-bold ${isPos ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                          {isPos ? '+' : ''}{d.shap_value.toFixed(2)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle text-center space-y-3">
              <Sliders size={36} className="text-slate-300 dark:text-slate-600 mx-auto" />
              <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">Ready for Simulation</h4>
              <p className="text-xs text-slate-600 dark:text-slate-300">
                Adjust any of the static or Git evolution sliders on the left, then click <b>Run Prediction</b> to inspect the defect-risk estimate and SHAP explanation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Simulator;

