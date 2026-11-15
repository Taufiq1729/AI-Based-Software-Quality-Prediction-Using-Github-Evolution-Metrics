import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  GitBranch, 
  BarChart3, 
  TrendingUp, 
  Award, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  Info,
  ShieldCheck,
  Zap,
  Activity
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid, 
  LineChart, 
  Line 
} from 'recharts';
import { useScan } from '../context/ScanContext';

const ModelEvaluation = () => {
  const { apiBase } = useScan();
  const [evalData, setEvalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('benchmarks'); // 'benchmarks' | 'testset' | 'curves'
  const [selectedCurveModel, setSelectedCurveModel] = useState('RandomForest');

  useEffect(() => {
    const fetchEvaluation = async () => {
      try {
        const response = await axios.get(`${apiBase}/api/model-evaluation`);
        setEvalData(response.data);
      } catch (err) {
        console.error('Error fetching model evaluation:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchEvaluation();
  }, [apiBase]);

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-500">
        <Activity className="animate-spin mx-auto mb-2 text-blue-600" size={32} />
        <p className="text-sm font-semibold">Loading empirical research benchmarks...</p>
      </div>
    );
  }

  const benchmarks = evalData?.research_benchmarks;
  const pipeline = evalData?.pipeline_evaluation;
  const featureImportance = evalData?.feature_importance || [];

  // Prepare ROC curve data for the selected model
  const curveData = [];
  const rawMetrics = pipeline?.raw_metrics;
  if (rawMetrics && rawMetrics[selectedCurveModel]) {
    const mStatic = rawMetrics[selectedCurveModel].static?.ROC_Curve;
    const mComb = rawMetrics[selectedCurveModel].combined?.ROC_Curve;
    if (mStatic && mComb) {
      const maxLen = Math.max(mStatic.fpr.length, mComb.fpr.length);
      for (let i = 0; i < maxLen; i += Math.ceil(maxLen / 60)) {
        curveData.push({
          fpr: Number((mComb.fpr[i] || mComb.fpr[mComb.fpr.length - 1]).toFixed(3)),
          tprCombined: Number((mComb.tpr[i] || mComb.tpr[mComb.tpr.length - 1]).toFixed(3)),
          tprStatic: Number((mStatic.tpr[i] || mStatic.tpr[mStatic.tpr.length - 1]).toFixed(3)),
        });
      }
    }
  }

  // Precision-Recall curve data
  const prData = [];
  if (rawMetrics && rawMetrics[selectedCurveModel]) {
    const prStatic = rawMetrics[selectedCurveModel].static?.PR_Curve;
    const prComb = rawMetrics[selectedCurveModel].combined?.PR_Curve;
    if (prStatic && prComb) {
      const maxLen = Math.max(prStatic.recall.length, prComb.recall.length);
      for (let i = 0; i < maxLen; i += Math.ceil(maxLen / 60)) {
        prData.push({
          recall: Number((prComb.recall[i] || prComb.recall[prComb.recall.length - 1]).toFixed(3)),
          precCombined: Number((prComb.precision[i] || prComb.precision[prComb.precision.length - 1]).toFixed(3)),
          precStatic: Number((prStatic.precision[i] || prStatic.precision[prStatic.precision.length - 1]).toFixed(3)),
        });
      }
    }
  }

  return (
    <div className="space-y-8 py-2 max-w-6xl mx-auto">
      {/* Page Title */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 text-xs font-semibold mb-2">
          <Award size={13} />
          <span>Research Evaluation & ML Benchmarks</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Model Performance & Research Benchmarks
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Comparing all six configurations across 12 Static OO Metrics vs Combined (Static + 3 Git Evolution Metrics).
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4">
        {[
          { id: 'benchmarks', label: '1. Research Evaluation (Official Paper)', icon: Award },
          { id: 'testset', label: '2. All 6 ML Configurations (Pipeline Test Split)', icon: Layers },
          { id: 'curves', label: '3. ROC & PR Curves', icon: BarChart3 },
          { id: 'importance', label: '4. Global Feature Importance', icon: Zap },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 text-xs font-bold flex items-center gap-2 border-b-2 transition ${
                active 
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400' 
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* SECTION 1: OFFICIAL RESEARCH PAPER BENCHMARKS */}
      {activeTab === 'benchmarks' && (
        <div className="space-y-6">
          {/* Scientific Disclaimer Alert */}
          <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 dark:bg-blue-950/20 dark:border-blue-900/60 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-3">
            <Info size={16} className="text-blue-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Official Paper Benchmark Results:</span>
              <p className="mt-0.5 leading-relaxed text-blue-800 dark:text-blue-300">
                {benchmarks?.disclaimer}
              </p>
            </div>
          </div>

          {/* Primary Model Highlight Banner */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-blue-100">Primary Champion Model</span>
                <h3 className="text-2xl font-extrabold mt-1">Combined Logistic Regression</h3>
                <p className="text-xs text-blue-100 mt-1 max-w-xl">
                  Chosen as the primary model for CodeQuality AI due to superior calibrated recall and robust explainability across real-world Java projects.
                </p>
              </div>

              <div className="flex gap-4 sm:border-l sm:border-white/20 sm:pl-6">
                <div>
                  <p className="text-xs text-blue-200">Average Precision</p>
                  <p className="text-2xl font-extrabold font-mono">0.0276</p>
                  <span className="text-[10px] text-emerald-300 font-bold">+36.0% vs Static</span>
                </div>
                <div>
                  <p className="text-xs text-blue-200">ROC-AUC</p>
                  <p className="text-2xl font-extrabold font-mono">0.7890</p>
                  <span className="text-[10px] text-emerald-300 font-bold">+0.0998 Delta</span>
                </div>
                <div>
                  <p className="text-xs text-blue-200">Recall</p>
                  <p className="text-2xl font-extrabold font-mono">56.0%</p>
                  <span className="text-[10px] text-blue-200">Defect Detection</span>
                </div>
              </div>
            </div>
          </div>

          {/* Benchmark Comparison Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Research Paper Benchmark Performance Matrix
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-slate-500 uppercase text-[10px] tracking-wider">
                    <th className="py-3 px-4 font-bold">Model Configuration</th>
                    <th className="py-3 px-4 font-bold text-right">Avg Precision (AP)</th>
                    <th className="py-3 px-4 font-bold text-right">ROC-AUC</th>
                    <th className="py-3 px-4 font-bold text-right">Precision</th>
                    <th className="py-3 px-4 font-bold text-right">Recall</th>
                    <th className="py-3 px-4 font-bold text-right">F1-Score</th>
                    <th className="py-3 px-4 font-bold text-right">Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                  {/* Logistic Regression */}
                  <tr className="bg-blue-50/20 dark:bg-blue-950/20 font-semibold">
                    <td className="py-3 px-4 font-sans text-blue-700 dark:text-blue-300">
                      ★ Logistic Regression (Combined) - Primary
                    </td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400 font-bold">0.0276</td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400 font-bold">0.7890</td>
                    <td className="py-3 px-4 text-right">0.0244</td>
                    <td className="py-3 px-4 text-right font-bold text-blue-600 dark:text-blue-400">0.5600</td>
                    <td className="py-3 px-4 text-right">0.0468</td>
                    <td className="py-3 px-4 text-right">0.7784</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-sans text-slate-600 dark:text-slate-400">
                      Logistic Regression (Static Only)
                    </td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.0203</td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.6892</td>
                    <td className="py-3 px-4 text-right">0.0185</td>
                    <td className="py-3 px-4 text-right">0.4500</td>
                    <td className="py-3 px-4 text-right">0.0355</td>
                    <td className="py-3 px-4 text-right">0.7410</td>
                  </tr>

                  {/* Random Forest */}
                  <tr className="bg-slate-50/40 dark:bg-slate-800/20">
                    <td className="py-3 px-4 font-sans text-slate-800 dark:text-slate-200">
                      Random Forest (Combined)
                    </td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400 font-bold">0.0160</td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400">0.7320</td>
                    <td className="py-3 px-4 text-right">0.0180</td>
                    <td className="py-3 px-4 text-right">0.4400</td>
                    <td className="py-3 px-4 text-right">0.0345</td>
                    <td className="py-3 px-4 text-right">0.8920</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-sans text-slate-600 dark:text-slate-400">
                      Random Forest (Static Only)
                    </td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.0104</td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.6810</td>
                    <td className="py-3 px-4 text-right">0.0125</td>
                    <td className="py-3 px-4 text-right">0.3500</td>
                    <td className="py-3 px-4 text-right">0.0241</td>
                    <td className="py-3 px-4 text-right">0.8850</td>
                  </tr>

                  {/* Decision Tree */}
                  <tr className="bg-slate-50/40 dark:bg-slate-800/20">
                    <td className="py-3 px-4 font-sans text-slate-800 dark:text-slate-200">
                      Decision Tree (Combined)
                    </td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400">0.0114</td>
                    <td className="py-3 px-4 text-right text-emerald-600 dark:text-emerald-400">0.6450</td>
                    <td className="py-3 px-4 text-right">0.0135</td>
                    <td className="py-3 px-4 text-right">0.3800</td>
                    <td className="py-3 px-4 text-right">0.0260</td>
                    <td className="py-3 px-4 text-right">0.8240</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-sans text-slate-600 dark:text-slate-400">
                      Decision Tree (Static Only)
                    </td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.0097</td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">0.5980</td>
                    <td className="py-3 px-4 text-right">0.0110</td>
                    <td className="py-3 px-4 text-right">0.3200</td>
                    <td className="py-3 px-4 text-right">0.0212</td>
                    <td className="py-3 px-4 text-right">0.8120</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Grouped Bar Chart: Average Precision Gain */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-5">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-2">
                Average Precision: Static vs Combined
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Demonstrates that adding Git Evolution Metrics improves AP across all three model architectures.
              </p>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={benchmarks?.chart_data?.ap_comparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} vertical={false} />
                    <XAxis dataKey="model" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 0.035]} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Static_AP" name="Static Only" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Combined_AP" name="Combined (+ Git Evolution)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-5">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-2">
                ROC-AUC: Static vs Combined
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Discrimination capability boosts significantly when revision frequency and churn are included.
              </p>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={benchmarks?.chart_data?.auc_comparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} vertical={false} />
                    <XAxis dataKey="model" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0.5, 0.9]} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Static_AUC" name="Static Only" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Combined_AUC" name="Combined (+ Git Evolution)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: LOCAL PIPELINE TEST SET EVALUATION */}
      {activeTab === 'testset' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-300">
            <span className="font-bold text-slate-900 dark:text-white">Pipeline Test Split Validation:</span> Evaluation of the 6 saved model checkpoints on the preprocessed 20% stratified test dataset (2,446 components).
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Test Set Performance Matrix
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-slate-500 uppercase text-[10px] tracking-wider font-bold">
                    <th className="py-3 px-4">Configuration</th>
                    <th className="py-3 px-4 text-right">ROC-AUC</th>
                    <th className="py-3 px-4 text-right">Precision</th>
                    <th className="py-3 px-4 text-right">Recall</th>
                    <th className="py-3 px-4 text-right">F1-Score</th>
                    <th className="py-3 px-4 text-right">Accuracy</th>
                    <th className="py-3 px-4 text-center">Confusion Matrix [TN, FP / FN, TP]</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                  {pipeline?.comparison_table?.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="py-3 px-4 font-sans font-semibold text-slate-900 dark:text-white">
                        {row.model}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-blue-600 dark:text-blue-400">
                        {row.ROC_AUC.toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-right">{row.Precision.toFixed(4)}</td>
                      <td className="py-3 px-4 text-right">{row.Recall.toFixed(4)}</td>
                      <td className="py-3 px-4 text-right font-bold">{row.F1_Score.toFixed(4)}</td>
                      <td className="py-3 px-4 text-right">{(row.Accuracy * 100).toFixed(2)}%</td>
                      <td className="py-3 px-4 text-center font-mono text-[11px] text-slate-500">
                        [{row.ConfusionMatrix[0]?.[0]}, {row.ConfusionMatrix[0]?.[1]} / {row.ConfusionMatrix[1]?.[0]}, {row.ConfusionMatrix[1]?.[1]}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: INTERACTIVE ROC & PR CURVES */}
      {activeTab === 'curves' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Receiver Operating Characteristic (ROC) & PR Curves
            </h3>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500 font-semibold">Model Family:</span>
              {['LogisticRegression', 'RandomForest', 'DecisionTree'].map((fam) => (
                <button
                  key={fam}
                  onClick={() => setSelectedCurveModel(fam)}
                  className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                    selectedCurveModel === fam
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
                  }`}
                >
                  {fam}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* ROC Curve */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-5">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-1">
                ROC Curve ({selectedCurveModel})
              </h4>
              <p className="text-xs text-slate-500 mb-3">True Positive Rate vs False Positive Rate</p>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={curveData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
                    <XAxis dataKey="fpr" type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="tprCombined" name="Combined (+ Git Evolution)" stroke="#3b82f6" strokeWidth={2.5} dot={false} />
                    <Line type="monotone" dataKey="tprStatic" name="Static Only" stroke="#94a3b8" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* PR Curve */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-5">
              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-1">
                Precision-Recall Curve ({selectedCurveModel})
              </h4>
              <p className="text-xs text-slate-500 mb-3">Precision across different recall thresholds</p>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
                    <XAxis dataKey="recall" type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="precCombined" name="Combined (+ Git Evolution)" stroke="#8b5cf6" strokeWidth={2.5} dot={false} />
                    <Line type="monotone" dataKey="precStatic" name="Static Only" stroke="#94a3b8" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: GLOBAL FEATURE IMPORTANCE */}
      {activeTab === 'importance' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Global Feature Importance (Random Forest Ensemble)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Relative Gini importance across the 15 metrics. Notice how Git evolution metrics rank among the strongest global predictors.
            </p>
          </div>

          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[...featureImportance].reverse()} layout="vertical" margin={{ left: 50, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis dataKey="feature" type="category" tick={{ fontSize: 11, fill: '#64748b' }} width={120} />
                <Tooltip 
                  formatter={(val) => [`${(val * 100).toFixed(2)}%`, 'Relative Importance']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Bar dataKey="importance" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelEvaluation;

