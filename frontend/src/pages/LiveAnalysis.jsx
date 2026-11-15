import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  Terminal, 
  ArrowRight, 
  GitBranch, 
  RotateCcw,
  ShieldCheck,
  FileCode,
  History,
  Cpu
} from 'lucide-react';
import { useScan } from '../context/ScanContext';

const STAGES = [
  { id: 1, name: 'Repository Validation', icon: ShieldCheck, threshold: 0.10 },
  { id: 2, name: 'Cloning & Git History Ingestion', icon: GitBranch, threshold: 0.30 },
  { id: 3, name: 'Java File Discovery', icon: FileCode, threshold: 0.45 },
  { id: 4, name: 'Static OO Metric Extraction (12 Features)', icon: FileCode, threshold: 0.70 },
  { id: 5, name: 'Git Evolution Mining (Churn, Revisions, Devs)', icon: History, threshold: 0.85 },
  { id: 6, name: 'ML Model Inference & Defect Risk Scoring', icon: Cpu, threshold: 1.0 }
];

const LiveAnalysis = () => {
  const navigate = useNavigate();
  const { currentTaskId, fetchScanResults, apiBase } = useScan();

  const [statusData, setStatusData] = useState(null);
  const [error, setError] = useState('');
  const [polling, setPolling] = useState(true);
  const logContainerRef = useRef(null);

  useEffect(() => {
    if (!currentTaskId) {
      navigate('/');
      return;
    }

    let interval = null;

    const pollStatus = async () => {
      try {
        const response = await axios.get(`${apiBase}/api/scan-status/${currentTaskId}`);
        const data = response.data;
        setStatusData(data);

        if (data.status === 'completed') {
          setPolling(false);
          if (interval) clearInterval(interval);
          await fetchScanResults(currentTaskId);
        } else if (data.status === 'failed') {
          setPolling(false);
          if (interval) clearInterval(interval);
          setError(data.error || 'Scan failed.');
        }
      } catch (err) {
        console.error('Error polling status:', err);
        const detail = err.response?.data?.detail;
        setError(detail || 'Scan task not found or server restarted. Please start a new scan.');
        setPolling(false);
        if (interval) clearInterval(interval);
      }
    };

    pollStatus();
    interval = setInterval(pollStatus, 1500);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentTaskId, apiBase, navigate]);

  // Auto-scroll log box
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [statusData?.logs]);

  const progress = statusData ? Math.round(statusData.progress * 100) : 5;
  const isCompleted = statusData?.status === 'completed';
  const isFailed = statusData?.status === 'failed';

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-8">
      {/* Title */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
          {isCompleted ? 'Analysis Complete!' : isFailed ? 'Analysis Failed' : 'Scanning Repository...'}
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {statusData?.message || 'Processing repository structure, mining Git commits, and calculating metrics.'}
        </p>
      </div>

      {/* Progress Bar Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
        <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-2">
            {!isCompleted && !isFailed && <Loader2 size={16} className="animate-spin text-blue-600" />}
            {isCompleted && <CheckCircle2 size={16} className="text-emerald-500" />}
            {isFailed && <AlertCircle size={16} className="text-red-500" />}
            <span>Pipeline Progress</span>
          </div>
          <span className="font-mono text-sm text-blue-600 dark:text-blue-400 font-extrabold">{progress}%</span>
        </div>

        {/* Outer bar */}
        <div className="w-full h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-200 dark:border-slate-700/60">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isFailed 
                ? 'bg-red-500' 
                : isCompleted 
                ? 'bg-emerald-500' 
                : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Repository Meta Pill if available */}
        {statusData?.repo_info && (
          <div className="pt-2 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800">
            <span>Repository: <b className="text-slate-800 dark:text-slate-200">{statusData.repo_info.owner}/{statusData.repo_info.name}</b></span>
            <span>Commits Scanned: <b className="text-slate-800 dark:text-slate-200">{statusData.repo_info.total_commits}</b></span>
            {statusData.repo_info.latest_commit && (
              <span>Commit: <code className="text-blue-600 dark:text-blue-400 font-mono">{statusData.repo_info.latest_commit}</code></span>
            )}
          </div>
        )}
      </div>

      {/* 6 Stage Workflow Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {STAGES.map((stage) => {
          const Icon = stage.icon;
          const isDone = (statusData?.progress || 0) >= stage.threshold || isCompleted;
          const isCurrent = !isDone && !isFailed && (statusData?.progress || 0) >= (stage.threshold - 0.20);

          return (
            <div
              key={stage.id}
              className={`p-4 rounded-xl border transition-all ${
                isDone
                  ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/50 text-slate-800 dark:text-slate-200'
                  : isCurrent
                  ? 'bg-blue-50/70 dark:bg-blue-950/40 border-blue-300 dark:border-blue-800 shadow-sm text-blue-900 dark:text-blue-200'
                  : 'bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 text-slate-400 dark:text-slate-500 opacity-60'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  isDone 
                    ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300' 
                    : isCurrent 
                    ? 'bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300' 
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                }`}>
                  {isDone ? (
                    <CheckCircle2 size={16} />
                  ) : isCurrent ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Icon size={16} />
                  )}
                </div>
                <div className="overflow-hidden">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-600 dark:text-slate-300 block">
                    Stage {stage.id}
                  </span>
                  <p className="text-xs font-semibold truncate mt-0.5">
                    {stage.name}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Terminal Log Stream */}
      <div className="bg-slate-950 text-slate-200 rounded-2xl border border-slate-800 shadow-xl overflow-hidden font-mono text-xs">
        <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-slate-400">
          <div className="flex items-center gap-2">
            <Terminal size={14} className="text-blue-400" />
            <span className="font-semibold text-xs text-slate-300">Pipeline Execution Stream</span>
          </div>
          <span className="text-[11px] text-slate-500">Live stdout</span>
        </div>

        <div
          ref={logContainerRef}
          className="p-4 h-52 overflow-y-auto space-y-1.5 scrollbar-thin scrollbar-thumb-slate-800 leading-relaxed"
        >
          {statusData?.logs?.map((log, index) => (
            <div key={index} className="flex gap-2 text-slate-300">
              <span className="text-slate-600 select-none">›</span>
              <span>{log}</span>
            </div>
          ))}
          {polling && (
            <div className="flex items-center gap-2 text-blue-400 animate-pulse pt-1">
              <span className="text-slate-600 select-none">›</span>
              <span>Processing stage...</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons when Done / Failed */}
      {isCompleted && (
        <div className="p-6 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <h3 className="text-base font-bold text-emerald-900 dark:text-emerald-200">
              Analysis Completed Successfully!
            </h3>
            <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-0.5">
              Source code AST metrics and Git evolution history have been combined and scored.
            </p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition flex items-center gap-2 shrink-0"
          >
            <span>Open Interactive Dashboard</span>
            <ArrowRight size={16} />
          </button>
        </div>
      )}

      {isFailed && (
        <div className="p-6 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <h3 className="text-base font-bold text-red-900 dark:text-red-200">
              Scan Failed
            </h3>
            <p className="text-xs text-red-700 dark:text-red-400 mt-0.5">
              {error}
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition flex items-center gap-2 shrink-0"
          >
            <RotateCcw size={14} />
            <span>Try Another Repository</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default LiveAnalysis;

