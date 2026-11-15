import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  X, 
  ShieldAlert, 
  ShieldCheck, 
  Copy, 
  Check, 
  BarChart3, 
  Info, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  FileCode,
  Layers,
  GitCommit,
  GitBranch,
  Activity
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar, 
  Legend 
} from 'recharts';
import { useScan } from '../context/ScanContext';
import MetricTooltip, { METRIC_DEFINITIONS } from './MetricTooltip';

const FileDetailModal = () => {
  const { 
    selectedFileForModal, 
    setSelectedFileForModal, 
    currentTaskId, 
    selectedModel,
    apiBase 
  } = useScan();

  const [detailData, setDetailData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'metrics' | 'shap'

  useEffect(() => {
    if (!selectedFileForModal) {
      setDetailData(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${apiBase}/api/file-detail/${currentTaskId}`, {
          params: {
            file_path: selectedFileForModal.file_path,
            model: selectedModel
          }
        });
        setDetailData(response.data);
      } catch (err) {
        console.error('Error fetching file detail:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [selectedFileForModal, currentTaskId, selectedModel, apiBase]);

  if (!selectedFileForModal) return null;

  const file = selectedFileForModal;
  const isHighRisk = file.risk_level === 'HIGH';

  const copyPath = () => {
    navigator.clipboard.writeText(file.file_path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const explanation = detailData?.explanation;
  const shapDrivers = explanation?.feature_contributions || [];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5">
      <div 
        className="relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className={`p-2.5 rounded-xl ${isHighRisk ? 'bg-red-50 text-red-600 dark:bg-red-950/60 dark:text-red-400' : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400'}`}>
              {isHighRisk ? <ShieldAlert size={22} /> : <ShieldCheck size={22} />}
            </div>
            <div className="overflow-hidden">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">
                  {file.file_name}
                </h3>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                  isHighRisk 
                    ? 'bg-red-100 text-red-700 dark:bg-red-950/70 dark:text-red-400 border border-red-200 dark:border-red-900' 
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900'
                }`}>
                  {file.risk_level} RISK ({(file.risk_score * 100).toFixed(1)}%)
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate flex items-center gap-1 font-mono mt-0.5">
                <span>{file.file_path}</span>
                <button 
                  onClick={copyPath}
                  className="p-1 hover:text-slate-700 dark:hover:text-slate-200 transition"
                  title="Copy path"
                >
                  {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                </button>
              </p>
            </div>
          </div>

          <button
            onClick={() => setSelectedFileForModal(null)}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Tabs inside Modal */}
        <div className="px-6 border-b border-slate-200 dark:border-slate-800 flex gap-4 bg-white dark:bg-slate-900">
          {[
            { id: 'overview', label: 'Diagnosis & Overview', icon: Sparkles },
            { id: 'metrics', label: 'All 15 Metrics', icon: Layers },
            { id: 'shap', label: 'SHAP Feature Drivers', icon: BarChart3 }
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
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

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* TAB 1: OVERVIEW & DIAGNOSIS */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Natural Language Diagnostic Alert Card */}
              <div className={`p-4 rounded-xl border ${
                isHighRisk 
                  ? 'bg-amber-50/70 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900/50' 
                  : 'bg-emerald-50/70 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/50'
              }`}>
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 p-1.5 rounded-lg ${
                    isHighRisk ? 'bg-amber-200/60 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300' : 'bg-emerald-200/60 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300'
                  }`}>
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                      AI Diagnostic Assessment
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                      {explanation?.narrative_explanation || file.explanation_summary || 'Analyzing metric signature...'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Top Metric Highlights Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Lines of Code (LOC)</p>
                  <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">{file.LOC}</p>
                  <span className="text-[10px] text-slate-600 dark:text-slate-300">Executable size</span>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Historical Churn</p>
                  <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">{file.code_churn}</p>
                  <span className="text-[10px] text-slate-600 dark:text-slate-300">Lines added + deleted</span>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Commit Revisions</p>
                  <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">{file.revision_count}</p>
                  <span className="text-[10px] text-slate-600 dark:text-slate-300">Commits touching file</span>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800">
                  <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Contributors</p>
                  <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">{file.developer_count}</p>
                  <span className="text-[10px] text-slate-600 dark:text-slate-300">Distinct developers</span>
                </div>
              </div>

              {/* Radar Comparison Chart (File vs Repo Average) */}
              {detailData?.radar_comparison && (
                <div className="p-4 bg-white dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-800">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-2">
                    Relative Structural Complexity (File vs Repository Average)
                  </h4>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="75%" data={detailData.radar_comparison}>
                        <PolarGrid stroke="#94a3b8" strokeOpacity={0.2} />
                        <PolarAngleAxis dataKey="metric" tick={{ fill: '#64748b', fontSize: 11 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 'auto']} tick={{ fill: '#64748b', fontSize: 9 }} />
                        <Radar name="This File" dataKey="file" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
                        <Radar name="Repo Average" dataKey="repo_avg" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.2} />
                        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ALL 15 METRICS */}
          {activeTab === 'metrics' && (
            <div className="space-y-6">
              {/* Static Metrics (12) */}
              <div>
                <h4 className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <FileCode size={14} className="text-blue-500" />
                  <span>12 Static Object-Oriented Metrics</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {[
                    { key: 'LOC', label: 'LOC - Lines of Code', val: file.LOC },
                    { key: 'WMC', label: 'WMC - Weighted Methods', val: file.WMC },
                    { key: 'DIT', label: 'DIT - Inheritance Depth', val: file.DIT },
                    { key: 'NOC', label: 'NOC - Number of Children', val: file.NOC },
                    { key: 'CBO', label: 'CBO - Coupling', val: file.CBO },
                    { key: 'RFC', label: 'RFC - Response For Class', val: file.RFC },
                    { key: 'LCOM5', label: 'LCOM5 - Cohesion Lack', val: file.LCOM5 },
                    { key: 'NPA', label: 'NPA - Public Attributes', val: file.NPA },
                    { key: 'NPM', label: 'NPM - Public Methods', val: file.NPM },
                    { key: 'NLE', label: 'NLE - Max Nesting Depth', val: file.NLE },
                    { key: 'CBOI', label: 'CBOI - Inverse Coupling', val: file.CBOI },
                    { key: 'CD', label: 'CD - Comment Density', val: (file.CD * 100).toFixed(1) + '%' },
                  ].map((m) => (
                    <div key={m.key} className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                      <div>
                        <MetricTooltip metricKey={m.key}>
                          <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{m.key}</span>
                        </MetricTooltip>
                        <p className="text-[11px] text-slate-600 dark:text-slate-300 truncate">{m.label.split(' - ')[1]}</p>
                      </div>
                      <span className="text-sm font-bold text-slate-900 dark:text-white">{m.val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evolution Metrics (3) */}
              <div>
                <h4 className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <GitCommit size={14} className="text-purple-500" />
                  <span>3 Git Evolution Metrics</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3.5 bg-purple-50/50 dark:bg-purple-950/20 rounded-xl border border-purple-200 dark:border-purple-900/50 flex items-center justify-between">
                    <div>
                      <MetricTooltip metricKey="code_churn">
                        <span className="text-xs font-bold text-purple-900 dark:text-purple-300">Code Churn</span>
                      </MetricTooltip>
                      <p className="text-[11px] text-slate-600 dark:text-slate-300">Total lines added + deleted</p>
                    </div>
                    <span className="text-base font-extrabold text-purple-700 dark:text-purple-300">{file.code_churn}</span>
                  </div>

                  <div className="p-3.5 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-xl border border-indigo-200 dark:border-indigo-900/50 flex items-center justify-between">
                    <div>
                      <MetricTooltip metricKey="revision_count">
                        <span className="text-xs font-bold text-indigo-900 dark:text-indigo-300">Revision Count</span>
                      </MetricTooltip>
                      <p className="text-[11px] text-slate-600 dark:text-slate-300">Commits modifying file</p>
                    </div>
                    <span className="text-base font-extrabold text-indigo-700 dark:text-indigo-300">{file.revision_count}</span>
                  </div>

                  <div className="p-3.5 bg-blue-50/50 dark:bg-blue-950/20 rounded-xl border border-blue-200 dark:border-blue-900/50 flex items-center justify-between">
                    <div>
                      <MetricTooltip metricKey="developer_count">
                        <span className="text-xs font-bold text-blue-900 dark:text-blue-300">Developer Count</span>
                      </MetricTooltip>
                      <p className="text-[11px] text-slate-600 dark:text-slate-300">Distinct commit authors</p>
                    </div>
                    <span className="text-base font-extrabold text-blue-700 dark:text-blue-300">{file.developer_count}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SHAP FEATURE DRIVERS */}
          {activeTab === 'shap' && (
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-1">
                  SHAP Feature Contributions
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  Explains how each individual metric pushed this file’s defect-risk score up (amplifying risk) or down (reducing risk).
                </p>
              </div>

              {shapDrivers.length > 0 ? (
                <div className="space-y-2">
                  {shapDrivers.map((item, idx) => {
                    const isPositive = item.shap_value > 0;
                    return (
                      <div 
                        key={idx}
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="flex items-center gap-2.5 overflow-hidden">
                          <div className={`p-1.5 rounded-lg ${isPositive ? 'bg-red-100 text-red-600 dark:bg-red-950/60 dark:text-red-400' : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400'}`}>
                            {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                          </div>
                          <div className="overflow-hidden">
                            <span className="font-semibold text-slate-800 dark:text-slate-200 block truncate">
                              {item.label}
                            </span>
                            <span className="text-[11px] text-slate-600 dark:text-slate-300">
                              Value: {item.raw_value}
                            </span>
                          </div>
                        </div>

                        <div className="text-right">
                          <span className={`font-mono font-bold ${isPositive ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                            {isPositive ? '+' : ''}{item.shap_value.toFixed(3)}
                          </span>
                          <span className="block text-[10px] text-slate-600 dark:text-slate-300 font-medium">
                            {isPositive ? 'Increases Risk' : 'Reduces Risk'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500">
                  <Activity className="animate-spin mx-auto mb-2 text-blue-500" />
                  <p>Calculating SHAP explanation vectors...</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
          <span>Active Model: <b>{file.model_used || selectedModel}</b></span>
          <button
            onClick={() => setSelectedFileForModal(null)}
            className="px-4 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default FileDetailModal;

