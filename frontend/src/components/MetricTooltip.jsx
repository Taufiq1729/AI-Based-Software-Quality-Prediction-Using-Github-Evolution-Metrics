import React, { useState } from 'react';
import { Info } from 'lucide-react';

export const METRIC_DEFINITIONS = {
  LOC: {
    name: 'Lines of Code (LOC)',
    description: 'Physical source lines of code excluding blank lines and standalone comments.',
    category: 'Static - Size',
    interpretation: 'Larger files tend to accumulate complexity and provide more surface area for defects.'
  },
  WMC: {
    name: 'Weighted Methods per Class (WMC)',
    description: 'Sum of cyclomatic complexity across all methods declared in the class.',
    category: 'Static - Complexity',
    interpretation: 'High WMC indicates complex branching, nested loops, and challenging testing paths.'
  },
  DIT: {
    name: 'Depth of Inheritance Tree (DIT)',
    description: 'Maximum distance from the class to the root Object in the inheritance hierarchy.',
    category: 'Static - Inheritance',
    interpretation: 'Deeper trees offer inheritance reuse but increase coupling to superclass behavior.'
  },
  NOC: {
    name: 'Number of Children (NOC)',
    description: 'Number of immediate subclasses directly extending this class in the project.',
    category: 'Static - Inheritance',
    interpretation: 'High NOC implies wide architectural impact if this base class is modified.'
  },
  CBO: {
    name: 'Coupling Between Object Classes (CBO)',
    description: 'Number of distinct non-primitive classes referenced via fields, parameters, returns, and calls.',
    category: 'Static - Coupling',
    interpretation: 'Excessive coupling makes the class vulnerable to upstream API alterations and refactor breaks.'
  },
  RFC: {
    name: 'Response for a Class (RFC)',
    description: 'Count of local methods plus foreign methods that can be executed by invoking this class.',
    category: 'Static - Coupling & Communication',
    interpretation: 'Higher RFC increases the cognitive load and testing effort required to verify execution paths.'
  },
  LCOM5: {
    name: 'Lack of Cohesion of Methods (LCOM5)',
    description: 'Henderson-Sellers metric evaluating how evenly class methods access instance variables.',
    category: 'Static - Cohesion',
    interpretation: 'LCOM5 approaching 1 or higher suggests multiple unrelated responsibilities (violates SRP).'
  },
  NPA: {
    name: 'Number of Public Attributes (NPA)',
    description: 'Count of non-private, public fields accessible from outside the class.',
    category: 'Static - Encapsulation',
    interpretation: 'High NPA violates encapsulation and leaks mutable internal state.'
  },
  NPM: {
    name: 'Number of Public Methods (NPM)',
    description: 'Count of public methods exposing the class interface.',
    category: 'Static - Interface Size',
    interpretation: 'Wide public interfaces require rigorous backwards compatibility guarantees.'
  },
  NLE: {
    name: 'Nesting Level Else-If (NLE)',
    description: 'Maximum depth of nested conditional blocks (if, else-if, for, while, switch).',
    category: 'Static - Control Flow',
    interpretation: 'Deep nesting creates cognitive strain and combinatorial explosion of test cases.'
  },
  CBOI: {
    name: 'Inverse Coupling / Afferent Coupling (CBOI)',
    description: 'Count of other repository classes that depend upon or reference this class.',
    category: 'Static - Architectural Coupling',
    interpretation: 'High CBOI indicates core utility classes whose defect risk cascades broadly.'
  },
  CD: {
    name: 'Comment Density (CD)',
    description: 'Ratio of comment lines to total lines (comments / [LOC + comments]).',
    category: 'Static - Documentation',
    interpretation: 'Healthy balance (~0.15 - 0.30) aids maintainability; near-zero indicates undocumented logic.'
  },
  code_churn: {
    name: 'Code Churn',
    description: 'Total lines added plus deleted across historical commits touching this file.',
    category: 'Git Evolution - Volatility',
    interpretation: 'High churn indicates intense volatility, frequently revised logic, and active bug fix churn.'
  },
  revision_count: {
    name: 'Revision Count',
    description: 'Total number of commits in Git history that modified this specific file.',
    category: 'Git Evolution - Activity',
    interpretation: 'High revisions mark hotspot files that are modified repeatedly during the project lifecycle.'
  },
  developer_count: {
    name: 'Developer Count',
    description: 'Total number of distinct engineers / commit authors who modified this file.',
    category: 'Git Evolution - Ownership',
    interpretation: 'Diffuse code ownership (>4-5 authors) without clear stewardship correlates with defect emergence.'
  }
};

const MetricTooltip = ({ metricKey, children }) => {
  const [show, setShow] = useState(false);
  const info = METRIC_DEFINITIONS[metricKey] || {
    name: metricKey,
    description: 'Software Quality Metric',
    category: 'Metric',
    interpretation: 'Quantitative indicator of code quality.'
  };

  return (
    <div className="relative inline-flex items-center gap-1 group">
      {children}
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition"
        aria-label="Metric information"
      >
        <Info size={13} />
      </button>

      {show && (
        <div 
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-72 p-3 bg-slate-900 text-white rounded-xl shadow-xl text-left border border-slate-700 pointer-events-none text-xs"
          role="tooltip"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-white">{info.name}</span>
            <span className="text-[10px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {info.category}
            </span>
          </div>
          <p className="text-slate-300 leading-relaxed mb-2">{info.description}</p>
          <div className="p-2 bg-slate-800/80 rounded-lg text-slate-300 text-[11px] border border-slate-700/50">
            <span className="font-medium text-amber-300">Impact: </span>
            {info.interpretation}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900"></div>
        </div>
      )}
    </div>
  );
};

export default MetricTooltip;

