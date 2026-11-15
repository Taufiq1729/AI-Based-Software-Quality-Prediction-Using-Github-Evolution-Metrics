import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Download, 
  ArrowUpDown, 
  Filter, 
  ShieldAlert, 
  ShieldCheck, 
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Sliders,
  FileCode,
  Info
} from 'lucide-react';
import { useScan } from '../context/ScanContext';

const FileExplorer = () => {
  const navigate = useNavigate();
  const { 
    scanResults, 
    currentTaskId, 
    selectedModel, 
    threshold, 
    setSelectedFileForModal,
    apiBase 
  } = useScan();

  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL'); // 'ALL' | 'HIGH' | 'LOW'
  const [sortField, setSortField] = useState('risk_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const rawFiles = scanResults?.files || [];

  // Filter and Sort files
  const filteredAndSortedFiles = useMemo(() => {
    let result = [...rawFiles];

    // Search filter
    if (searchTerm.trim()) {
      const lower = searchTerm.toLowerCase();
      result = result.filter(f => 
        f.file_name.toLowerCase().includes(lower) || 
        f.file_path.toLowerCase().includes(lower)
      );
    }

    // Risk level filter
    if (riskFilter !== 'ALL') {
      result = result.filter(f => f.risk_level === riskFilter);
    }

    // Sort
    result.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (typeof valA === 'string') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
      }

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });

    return result;
  }, [rawFiles, searchTerm, riskFilter, sortField, sortAsc]);

  // Pagination slice
  const totalPages = Math.ceil(filteredAndSortedFiles.length / pageSize) || 1;
  const paginatedFiles = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedFiles.slice(start, start + pageSize);
  }, [filteredAndSortedFiles, currentPage, pageSize]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false); // Default to desc for risk
    }
  };

  if (!currentTaskId || !scanResults) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto">
          <FileCode size={32} />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">No Files Analyzed Yet</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Run a repository scan to generate file-level defect predictions.
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

  return (
    <div className="space-y-6 py-2">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            File-Level Defect Risk Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Showing {filteredAndSortedFiles.length} of {rawFiles.length} analyzed Java files in <b>{scanResults.repo_info?.name}</b>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={`${apiBase}/api/export-csv/${currentTaskId}?model=${selectedModel}&threshold=${threshold}`}
            download
            className="px-4 py-2 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-bold text-xs transition flex items-center gap-2 shadow-sm"
          >
            <Download size={14} />
            <span>Export CSV Report</span>
          </a>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search input */}
        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search by file or path..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Filter size={13} />
            <span>Risk Level:</span>
          </span>
          {['ALL', 'HIGH', 'LOW'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => {
                setRiskFilter(lvl);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                riskFilter === lvl
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {lvl === 'ALL' ? 'All Files' : lvl === 'HIGH' ? 'High Risk' : 'Low Risk'}
            </button>
          ))}
        </div>

        {/* Rows per page selector */}
        <div className="flex items-center gap-2 text-xs text-slate-500 w-full md:w-auto justify-end">
          <span>Rows:</span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="px-2 py-1 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200"
          >
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Main Files Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-subtle overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-slate-500 uppercase text-[10px] tracking-wider select-none">
                <th 
                  onClick={() => handleSort('file_name')}
                  className="py-3 px-4 font-bold cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center gap-1">
                    <span>File Name</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('LOC')}
                  className="py-3 px-4 font-bold text-right cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>LOC</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('code_churn')}
                  className="py-3 px-4 font-bold text-right cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Code Churn</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('revision_count')}
                  className="py-3 px-4 font-bold text-right cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Revisions</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('developer_count')}
                  className="py-3 px-4 font-bold text-right cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Developers</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('risk_score')}
                  className="py-3 px-4 font-bold text-right cursor-pointer hover:text-blue-600 transition"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Risk Score</span>
                    <ArrowUpDown size={11} />
                  </div>
                </th>
                <th className="py-3 px-4 font-bold text-center">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {paginatedFiles.length > 0 ? (
                paginatedFiles.map((file, idx) => {
                  const isHigh = file.risk_level === 'HIGH';
                  return (
                    <tr
                      key={idx}
                      onClick={() => setSelectedFileForModal(file)}
                      className={`hover:bg-blue-50/60 dark:hover:bg-slate-800/60 cursor-pointer transition ${
                        isHigh ? 'bg-red-50/15 dark:bg-red-950/10' : ''
                      }`}
                    >
                      {/* File Name & Path */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <FileCode size={15} className={isHigh ? 'text-red-500' : 'text-slate-400'} />
                          <div className="overflow-hidden">
                            <span className="font-semibold text-slate-900 dark:text-white block hover:text-blue-600 transition">
                              {file.file_name}
                            </span>
                            <span className="text-[11px] text-slate-600 dark:text-slate-300 font-mono block truncate max-w-sm">
                              {file.file_path}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* LOC */}
                      <td className="py-3 px-4 text-right font-mono text-slate-700 dark:text-slate-300">
                        {file.LOC}
                      </td>

                      {/* Code Churn */}
                      <td className="py-3 px-4 text-right font-mono font-semibold text-purple-700 dark:text-purple-300">
                        {file.code_churn.toLocaleString()}
                      </td>

                      {/* Revision Count */}
                      <td className="py-3 px-4 text-right font-mono text-slate-700 dark:text-slate-300">
                        {file.revision_count}
                      </td>

                      {/* Developer Count */}
                      <td className="py-3 px-4 text-right font-mono text-slate-700 dark:text-slate-300">
                        {file.developer_count}
                      </td>

                      {/* Risk Score */}
                      <td className="py-3 px-4 text-right font-mono font-bold text-sm">
                        <span className={isHigh ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}>
                          {(file.risk_score * 100).toFixed(1)}%
                        </span>
                      </td>

                      {/* Risk Level Badge */}
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          isHigh 
                            ? 'bg-red-100 text-red-700 dark:bg-red-950/70 dark:text-red-400 border border-red-200 dark:border-red-900' 
                            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900'
                        }`}>
                          {isHigh ? <ShieldAlert size={11} /> : <ShieldCheck size={11} />}
                          <span>{file.risk_level}</span>
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No files match the current search or risk filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between text-xs text-slate-500">
          <span>
            Page <b>{currentPage}</b> of <b>{totalPages}</b> ({filteredAndSortedFiles.length} total files)
          </span>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileExplorer;

