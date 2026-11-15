import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Search, 
  GitBranch, 
  Layers, 
  ShieldCheck, 
  Cpu, 
  ArrowRight, 
  Sparkles, 
  AlertCircle, 
  CheckCircle2, 
  Sliders, 
  Code2, 
  History,
  TrendingUp,
  FileSearch
} from 'lucide-react';
import { useScan } from '../context/ScanContext';

const SAMPLE_REPOS = [
  { name: 'google/gson', url: 'https://github.com/google/gson', desc: 'JSON parser/serializer (~150 files)' },
  { name: 'junit-team/junit4', url: 'https://github.com/junit-team/junit4', desc: 'Java testing framework (~280 files)' },
  { name: 'apache/commons-lang', url: 'https://github.com/apache/commons-lang', desc: 'Core Java utilities (~350 files)' },
  { name: 'square/retrofit', url: 'https://github.com/square/retrofit', desc: 'JVM HTTP client (~180 files)' }
];

const Home = () => {
  const navigate = useNavigate();
  const { setCurrentTaskId, selectedModel, setSelectedModel, threshold, setThreshold, apiBase } = useScan();

  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [isValidUrl, setIsValidUrl] = useState(false);

  const handleUrlChange = (e) => {
    const val = e.target.value;
    setRepoUrl(val);
    setValidationError('');

    const githubRegex = /^(https?:\/\/)?(www\.)?github\.com\/[\w\.-]+\/[\w\.-]+(\.git)?\/?$/;
    if (val.trim() && githubRegex.test(val.trim())) {
      setIsValidUrl(true);
    } else {
      setIsValidUrl(false);
    }
  };

  const handleSelectSample = (url) => {
    setRepoUrl(url);
    setValidationError('');
    setIsValidUrl(true);
  };

  const handleStartScan = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      setValidationError('Please enter a valid GitHub repository URL.');
      return;
    }

    setLoading(true);
    setValidationError('');

    try {
      const response = await axios.post(`${apiBase}/api/scan-repo`, {
        url: repoUrl.trim(),
        model_name: selectedModel,
        threshold: threshold
      });

      const taskId = response.data.task_id;
      setCurrentTaskId(taskId);
      navigate('/analysis');
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || 'Failed to start scan.';
      setValidationError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-12 py-4">
      {/* Hero Header */}
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200/80 dark:border-blue-800 text-xs font-semibold tracking-wide shadow-sm">
          <Sparkles size={13} className="text-blue-600 dark:text-blue-400" />
          <span>Research-Grade Software Quality & Defect Prediction</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
          Predict Java Defect Risk with{' '}
          <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
            GitHub Evolution Metrics
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
          Empirical software engineering proves that static code metrics alone overlook crucial bug hotspots. 
          CodeQuality AI unites <b>12 Object-Oriented Static Metrics</b> with <b>3 Git Evolution Metrics</b> (churn, revisions, developers) 
          using trained Machine Learning models to prioritize testing and code reviews.
        </p>
      </section>

      {/* Main Repository Input Card */}
      <section className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-none p-6 sm:p-8 space-y-6">
          <form onSubmit={handleStartScan} className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2">
                Public GitHub Repository URL
              </label>
              <div className="relative">
                <input
                  type="url"
                  placeholder="https://github.com/owner/repository"
                  value={repoUrl}
                  onChange={handleUrlChange}
                  className="w-full px-4 py-3.5 pl-11 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition shadow-inner"
                  required
                />
                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                {isValidUrl && (
                  <CheckCircle2 size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-emerald-500" />
                )}
              </div>
              {validationError && (
                <div className="flex items-center gap-2 mt-2 text-xs text-red-600 dark:text-red-400 font-medium">
                  <AlertCircle size={14} />
                  <span>{validationError}</span>
                </div>
              )}
            </div>

            {/* Quick Sample Selector Pills */}
            <div>
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
                Quick Test Repositories:
              </p>
              <div className="flex flex-wrap gap-2">
                {SAMPLE_REPOS.map((sample) => (
                  <button
                    key={sample.name}
                    type="button"
                    onClick={() => handleSelectSample(sample.url)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-blue-50 dark:bg-slate-800 dark:hover:bg-blue-950/40 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 border border-slate-200 dark:border-slate-700 transition"
                  >
                    {sample.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Model & Threshold Controls */}
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  ML Prediction Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="LogisticRegression_combined">Logistic Regression (Combined) ★ Primary</option>
                  <option value="LogisticRegression_static">Logistic Regression (Static Only)</option>
                  <option value="RandomForest_combined">Random Forest (Combined)</option>
                  <option value="RandomForest_static">Random Forest (Static Only)</option>
                  <option value="DecisionTree_combined">Decision Tree (Combined)</option>
                  <option value="DecisionTree_static">Decision Tree (Static Only)</option>
                </select>
                <span className="block text-[11px] text-slate-600 dark:text-slate-300 mt-1">
                  Combines 12 static metrics with 3 Git evolution metrics.
                </span>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    Defect Risk Threshold: {threshold.toFixed(2)}
                  </label>
                  <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400">
                    {threshold === 0.5 ? '(Default 0.50)' : 'Custom'}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                  <span>0.1 (Sensitive)</span>
                  <span>0.5 (Balanced)</span>
                  <span>0.9 (Conservative)</span>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-6 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg shadow-blue-500/25 disabled:opacity-50 transition transform active:scale-[0.99] flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Initializing Repository Scan...</span>
                </>
              ) : (
                <>
                  <FileSearch size={18} />
                  <span>Analyze Repository Quality</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-slate-600 dark:text-slate-300 flex items-center justify-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-500" />
            <span>Java repositories only. Risk scores represent relative defect prioritization indicators.</span>
          </div>
        </div>
      </section>

      {/* Feature Breakdown Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle hover:shadow-card transition">
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4">
            <Code2 size={22} />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">12 Static OO Metrics</h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Real AST parser extraction of Chidamber & Kemerer (CK) metrics: LOC, WMC, DIT, NOC, CBO, RFC, LCOM5, NPA, NPM, NLE, CBOI, and Comment Density.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle hover:shadow-card transition">
          <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-4">
            <History size={22} />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">3 Git Evolution Metrics</h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Mines repository commit history preserving file renames: historical code churn (lines added + deleted), revision frequency, and distinct developer count.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle hover:shadow-card transition">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4">
            <Cpu size={22} />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">6 ML Model Configurations</h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Pre-trained Logistic Regression, Random Forest, and Decision Tree classifiers with full SHAP explainability and interactive model comparison.
          </p>
        </div>
      </section>

      {/* Benchmark Research Banner */}
      <section className="max-w-5xl mx-auto p-6 rounded-2xl bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1 text-center md:text-left">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold mb-1">
            <TrendingUp size={13} />
            <span>Empirical Paper Benchmark</span>
          </div>
          <h3 className="text-lg font-bold">Evolution Metrics Deliver +36.0% Average Precision Gain</h3>
          <p className="text-xs text-slate-300 max-w-xl">
            In benchmark evaluations, combining Git history with static code metrics increased Logistic Regression AP from 0.0203 to 0.0276 and ROC-AUC from 0.6892 to 0.7890.
          </p>
        </div>
        <button
          onClick={() => navigate('/models')}
          className="px-5 py-2.5 rounded-xl bg-white text-slate-900 font-bold text-xs hover:bg-slate-100 transition shadow flex items-center gap-2 shrink-0"
        >
          <span>View Model Evaluation</span>
          <ArrowRight size={14} />
        </button>
      </section>
    </div>
  );
};

export default Home;
