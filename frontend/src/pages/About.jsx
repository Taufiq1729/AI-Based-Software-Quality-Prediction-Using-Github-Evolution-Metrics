import React from 'react';
import { 
  BookOpen, 
  Layers, 
  History, 
  Cpu, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Code2, 
  Layers3,
  GitBranch,
  SlidersHorizontal,
  ExternalLink 
} from 'lucide-react';
import { METRIC_DEFINITIONS } from '../components/MetricTooltip';

const workflow = [
  'Submit a public Git repository URL.',
  'The backend clones the repository and records its checked-out commit.',
  'Java source files are discovered and parsed into compilation units.',
  'Twelve static code metrics are extracted from each supported primary file-level class.',
  'Git history is mined for code churn, revision count, and distinct developer count.',
  'The scanner assembles the ordered 15-feature vector for each file-level result.',
  'Training-time feature medians fill missing values, then the saved StandardScaler transforms the vector.',
  'Combined Logistic Regression produces a relative defect-risk score.',
  'Files are sorted by model score; individual class metrics and SHAP explanations are cached.',
  'The interactive dashboard presents the repository summary, diagnostics, ranked files, and charts.',
];

const About = () => {
  return (
    <div className="space-y-10 py-2 max-w-4xl mx-auto">
      {/* Title */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 text-xs font-semibold mb-2">
          <BookOpen size={13} />
          <span>Research Methodology & Metric Reference</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          About CodeQuality AI
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Theoretical foundation, experimental design, and comprehensive dictionary of software quality metrics.
        </p>
      </div>

      {/* Research Background & Problem Statement */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Layers size={18} className="text-blue-600" />
          <span>Research Motivation: Why Static Metrics Alone Fall Short</span>
        </h2>
        <div className="text-xs text-slate-600 dark:text-slate-300 space-y-3 leading-relaxed">
          <p>
            Traditional software quality assurance (SQA) relies heavily on static code metrics derived from class diagrams or abstract syntax trees (such as the Chidamber & Kemerer metric suite: WMC, DIT, NOC, CBO, RFC, and LCOM). While static metrics capture structural complexity and coupling, they present only a <b>static snapshot</b> of the source code.
          </p>
          <p>
            A class with high cyclomatic complexity may remain completely stable and bug-free for years if rarely modified. Conversely, an apparently simple class undergoing rapid, contested edits by multiple developers often becomes a hotbed for regressions.
          </p>
          <p>
            <b>CodeQuality AI</b> operationalizes the hypothesis that combining static object-oriented structural metrics with dynamic <b>Git Evolution Metrics</b> (Code Churn, Revision Frequency, and Developer Ownership Distribution) drastically enhances Machine Learning defect prediction accuracy—producing an empirical <b>+36% boost in Average Precision</b>.
          </p>
        </div>
      </section>

      {/* 10-Step Scanning Workflow */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Layers3 size={18} className="text-indigo-600" />
          <span>10-Stage Analysis Workflow</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {workflow.map((step, index) => (
            <div key={index} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-slate-700/60 flex items-start gap-3">
              <span className="font-mono text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-950/80 px-2 py-0.5 rounded-md shrink-0">
                {String(index + 1).padStart(2, '0')}
              </span>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">{step}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 15 Metrics Dictionary */}
      <section className="space-y-4">
        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Code2 size={18} className="text-purple-600" />
          <span>Complete Dictionary of 15 Software Quality Metrics</span>
        </h2>

        {/* 12 Static Metrics Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              12 Static Object-Oriented Metrics
            </h3>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
            {Object.entries(METRIC_DEFINITIONS)
              .filter(([_, info]) => info.category.startsWith('Static'))
              .map(([key, info]) => (
                <div key={key} className="p-4 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 dark:text-white font-mono">{key}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                      {info.category}
                    </span>
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 font-medium">{info.name}</p>
                  <p className="text-slate-500 text-[11px] leading-relaxed">{info.description}</p>
                  <div className="mt-1 text-[11px] text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg">
                    <span className="font-semibold text-slate-700 dark:text-slate-300">Engineering Impact: </span>
                    {info.interpretation}
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* 3 Evolution Metrics Table */}
        <div className="bg-white dark:bg-slate-900 border border-purple-200 dark:border-purple-900/50 rounded-2xl shadow-subtle overflow-hidden">
          <div className="px-5 py-3 border-b border-purple-200 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-950/30">
            <h3 className="text-xs font-bold uppercase tracking-wider text-purple-800 dark:text-purple-300">
              3 Git Evolution Metrics
            </h3>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
            {Object.entries(METRIC_DEFINITIONS)
              .filter(([_, info]) => info.category.startsWith('Git'))
              .map(([key, info]) => (
                <div key={key} className="p-4 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-purple-900 dark:text-purple-300 font-mono">{key}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300">
                      {info.category}
                    </span>
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 font-medium">{info.name}</p>
                  <p className="text-slate-500 text-[11px] leading-relaxed">{info.description}</p>
                  <div className="mt-1 text-[11px] text-slate-600 dark:text-slate-400 bg-purple-50/30 dark:bg-slate-800/50 p-2 rounded-lg">
                    <span className="font-semibold text-purple-700 dark:text-purple-300">Engineering Impact: </span>
                    {info.interpretation}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </section>

      {/* Scientific Constraints and Limitations */}
      <section className="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 rounded-2xl p-6 space-y-3">
        <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200 flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-600" />
          <span>Research Constraints & Ethical Usage Guidelines</span>
        </h3>
        <ul className="text-xs text-amber-900/80 dark:text-amber-300/80 space-y-2 list-disc list-inside leading-relaxed">
          <li>
            <b>Java Language Scope:</b> The current AST grammar and trained feature extractors are specialized for Java (.java) source files. Other languages (Python, JavaScript, Go) are not supported.
          </li>
          <li>
            <b>Relative Risk Indicator:</b> The defect-risk score is a relative ranking and prioritization metric. It denotes which files have statistical signatures resembling historical bug fixes, <b>not</b> certified defects or calibrated probabilities.
          </li>
          <li>
            <b>Non-Punitive Tooling:</b> Defect prediction metrics should be used constructively to schedule code reviews, pair programming, and focused automated testing—never for punitive developer appraisal.
          </li>
        </ul>
      </section>
    </div>
  );
};

export default About;
