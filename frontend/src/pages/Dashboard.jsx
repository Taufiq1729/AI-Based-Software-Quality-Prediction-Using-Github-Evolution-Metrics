import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ShieldAlert, 
  ShieldCheck, 
  FileCode, 
  GitCommit, 
  Users, 
  TrendingUp, 
  Download, 
  ExternalLink, 
  Sliders, 
  ArrowUpDown, 
  Info, 
  Sparkles,
  BarChart2,
  PieChart as PieIcon,
  RefreshCw
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid 
} from 'recharts';
import { useScan } from '../context/ScanContext';

const COLORS = ['#ef4444', '#22c55e', '#3b82f6', '#8b5cf6', '#f59e0b'];

const Dashboard = () => {
  const navigate = useNavigate();
  const { 
    scanResults, 
    loadingResults, 
    currentTaskId, 
    selectedModel, 
    threshold, 
    updateModelOrThreshold, 
    setSelectedFileForModal,
    apiBase 
  } = useScan();

  const [activeModel, setActiveModel] = useState(selectedModel);
  const [activeThreshold, setActiveThreshold] = useState(threshold);

  if (!currentTaskId || !scanResults) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto">
          <FileCode size={32} />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">No Active Repository Scan</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Please input a public GitHub repository to analyze software quality metrics and defect predictions.
        </p>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md transition"
        >
          Scan a Repository
        </button>
      </div>
    );
  }

  const { repo_info, repo_summary, summary, distribution, files } = scanResults;

  const handleApplyControls = () => {
    updateModelOrThreshold(activeModel, activeThreshold);
  };

  const pieData = [
    { name: 'High Risk', value: summary.high_risk_count, color: '#ef4444' },
    { name: 'Low Risk', value: summary.low_risk_count, color: '#22c55e' }
  ];

  const bucketData = distribution?.buckets || [];
  const topRiskFiles = distribution?.top_risk_files || [];

  return (
    <div className="space-y-8 py-2">
      {/* Top Header Card: Repo info & Quick Stats */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                Java Repository
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs text-slate-500 font-medium">Scanned via Git AST Pipeline</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1 flex items-center gap-2">
              <span>{repo_info?.name || 'Project Quality Dashboard'}</span>
              <a
                href={repo_info?.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition"
                title="Open on GitHub"
              >
                <ExternalLink size={18} />
              </a>
            </h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">{repo_info?.url}</p>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex items-center gap-2.5">
            <a
              href={`${apiBase}/api/export-csv/${currentTaskId}?model=${selectedModel}&threshold=${threshold}`}
              download
              className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold text-xs transition flex items-center gap-2 shadow-sm"
            >
              <Download size={15} />
              <span>Export CSV</span>
            </a>
            <button
              onClick={() => navigate('/files')}
              className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 transition flex items-center gap-2"
            >
              <span>Explore All Files ({summary.total_analyzed})</span>
            </button>
          </div>
        </div>

        {/* Dynamic Controls Bar: Threshold Slider & Model Switcher */}
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          <div className="md:col-span-5 flex items-center gap-3">
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Sliders size={13} className="text-blue-600" />
                  <span>Risk Threshold: {activeThreshold.toFixed(2)}</span>
                </span>
                <span className="text-[11px] text-slate-400">
                  {activeThreshold === 0.5 ? 'Default (0.50)' : 'Custom'}
                </span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={activeThreshold}
                onChange={(e) => setActiveThreshold(parseFloat(e.target.value))}
                className="w-full accent-blue-600 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          <div className="md:col-span-5">
            <span className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Active Machine Learning Model
            </span>
            <select
              value={activeModel}
              onChange={(e) => setActiveModel(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="LogisticRegression_combined">Logistic Regression (Combined) ★ Primary</option>
              <option value="LogisticRegression_static">Logistic Regression (Static Only)</option>
              <option value="RandomForest_combined">Random Forest (Combined)</option>
              <option value="RandomForest_static">Random Forest (Static Only)</option>
              <option value="DecisionTree_combined">Decision Tree (Combined)</option>
              <option value="DecisionTree_static">Decision Tree (Static Only)</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <button
              onClick={handleApplyControls}
              disabled={loadingResults || (activeModel === selectedModel && activeThreshold === threshold)}
              className="w-full py-2 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white font-bold text-xs disabled:opacity-40 transition flex items-center justify-center gap-1.5 shadow-sm"
            >
              <RefreshCw size={12} className={loadingResults ? 'animate-spin' : ''} />
              <span>{loadingResults ? 'Scoring...' : 'Apply Filter'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards Grid (8 Core Metrics) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Total Java Files */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <FileCode size={15} className="text-blue-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Java Files</span>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-white">{summary.total_analyzed}</p>
          <span className="text-[11px] text-slate-600 dark:text-slate-300">AST parsed classes</span>
        </div>

        {/* High-Risk Files */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-red-200 dark:border-red-900/50 rounded-2xl shadow-subtle bg-red-50/20 dark:bg-red-950/10">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-1">
            <ShieldAlert size={15} />
            <span className="text-[11px] font-bold uppercase tracking-wider">High Risk</span>
          </div>
          <p className="text-2xl font-extrabold text-red-600 dark:text-red-400">{summary.high_risk_count}</p>
          <span className="text-[11px] text-red-700 dark:text-red-300 font-semibold">{summary.high_risk_percentage}% of total</span>
        </div>

        {/* Low-Risk Files */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900/50 rounded-2xl shadow-subtle bg-emerald-50/20 dark:bg-emerald-950/10">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-1">
            <ShieldCheck size={15} />
            <span className="text-[11px] font-bold uppercase tracking-wider">Low Risk</span>
          </div>
          <p className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">{summary.low_risk_count}</p>
          <span className="text-[11px] text-emerald-700 dark:text-emerald-300 font-semibold">{summary.low_risk_percentage}% of total</span>
        </div>

        {/* Average Risk Score */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <TrendingUp size={15} className="text-indigo-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Avg Defect Risk</span>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-white">
            {(summary.average_risk_score * 100).toFixed(1)}%
          </p>
          <span className="text-[11px] text-slate-600 dark:text-slate-300">Mean file probability</span>
        </div>

        {/* Total Commits Analyzed */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <GitCommit size={15} className="text-purple-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Commits Mined</span>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-white">{repo_summary?.total_commits || 0}</p>
          <span className="text-[11px] text-slate-600 dark:text-slate-300">Git history depth</span>
        </div>

        {/* Total Developers Identified */}
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <Users size={15} className="text-amber-600" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Contributors</span>
          </div>
          <p className="text-2xl font-extrabold text-slate-900 dark:text-white">{repo_summary?.total_developers || 0}</p>
          <span className="text-[11px] text-slate-600 dark:text-slate-300">Distinct commit authors</span>
        </div>
      </div>

      {/* Visualizations Section: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: High-Risk vs Low-Risk Donut Chart (4 cols) */}
        <div className="lg:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              <PieIcon size={16} className="text-blue-600" />
              <span>Risk Classification Ratio</span>
            </h3>
            <p className="text-xs text-slate-500">Based on active threshold ({threshold.toFixed(2)})</p>
          </div>

          <div className="h-60 w-full my-auto">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(val) => [`${val} files (${((val / summary.total_analyzed) * 100).toFixed(1)}%)`, 'Count']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl text-center text-xs text-slate-600 dark:text-slate-300">
            <b>{summary.high_risk_count} files</b> flagged for priority testing
          </div>
        </div>

        {/* Right: Risk Distribution Across Score Ranges (8 cols) */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle p-5">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              <BarChart2 size={16} className="text-purple-600" />
              <span>Defect Risk Score Distribution</span>
            </h3>
            <p className="text-xs text-slate-500">
              Distribution of predicted risk probabilities across 5 severity tiers.
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bucketData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip 
                  formatter={(val) => [`${val} files`, 'File Count']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]}>
                  {bucketData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={index >= 3 ? '#ef4444' : index === 2 ? '#f59e0b' : '#3b82f6'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top 10 Highest Risk Files Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldAlert size={18} className="text-red-500" />
              <span>Top 10 Defect Hotspot Candidates</span>
            </h3>
            <p className="text-xs text-slate-500">
              Files exhibiting the highest predicted risk scores. Click any file to open deep-dive SHAP diagnostics.
            </p>
          </div>

          <button
            onClick={() => navigate('/files')}
            className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
          >
            View all {summary.total_analyzed} files →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                <th className="py-2.5 px-3">File Name</th>
                <th className="py-2.5 px-3">Relative Path</th>
                <th className="py-2.5 px-3 text-right">LOC</th>
                <th className="py-2.5 px-3 text-right">Code Churn</th>
                <th className="py-2.5 px-3 text-right">Defect Risk</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {files.slice(0, 10).map((file, idx) => (
                <tr
                  key={idx}
                  onClick={() => setSelectedFileForModal(file)}
                  className="hover:bg-blue-50/50 dark:hover:bg-slate-800/60 cursor-pointer transition"
                >
                  <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[11px] w-4">{idx + 1}.</span>
                    <span>{file.file_name}</span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px] truncate max-w-xs">
                    {file.file_path}
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300 font-mono">
                    {file.LOC}
                  </td>
                  <td className="py-2.5 px-3 text-right text-purple-700 dark:text-purple-300 font-mono font-semibold">
                    {file.code_churn}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="font-mono font-bold text-red-600 dark:text-red-400">
                      {(file.risk_score * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-950/70 dark:text-red-400 border border-red-200 dark:border-red-900">
                      High Risk
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scientific Disclaimer Note */}
      <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-300 flex items-start gap-3">
        <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <b>Research Note:</b> {summary.disclaimer}
        </p>
      </div>
    </div>
  );
};

export default Dashboard;

