import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Home, 
  Activity, 
  LayoutDashboard, 
  FolderTree, 
  GitFork, 
  Cpu, 
  HelpCircle, 
  Sun, 
  Moon, 
  ShieldCheck, 
  Menu, 
  X,
  ExternalLink
} from 'lucide-react';
import { useScan } from '../context/ScanContext';

const Navigation = () => {
  const { theme, toggleTheme, currentTaskId, scanResults } = useScan();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { name: 'Home', path: '/', icon: Home },
    { name: 'Live Analysis', path: '/analysis', icon: Activity, badge: currentTaskId ? 'Active' : null },
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'File Explorer', path: '/files', icon: FolderTree },
    { name: 'Model Evaluation', path: '/models', icon: GitFork },
    { name: 'Interactive Simulator', path: '/simulator', icon: Cpu },
    { name: 'About & Metrics', path: '/about', icon: HelpCircle },
  ];

  return (
    <>
      {/* Mobile Top Header */}
      <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <ShieldCheck size={20} />
          </div>
          <div>
            <span className="font-bold text-slate-900 dark:text-white tracking-tight">CodeQuality</span>
            <span className="text-blue-600 dark:text-blue-400 font-bold ml-1 text-xs px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-800">AI</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun size={18} className="text-amber-400" /> : <Moon size={18} className="text-slate-600" />}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </header>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-[57px] z-30 bg-slate-900/40 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)}>
          <div 
            className="bg-white dark:bg-slate-900 w-64 h-full p-4 border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between shadow-xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 font-semibold'
                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon size={18} className={isActive ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500'} />
                      <span>{item.name}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
            {scanResults && (
              <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/60 text-xs">
                <p className="text-slate-500 dark:text-slate-400 font-medium">Active Repo</p>
                <p className="font-semibold text-slate-800 dark:text-slate-200 truncate mt-0.5">
                  {scanResults.repo_info?.name || 'Analyzed Project'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Desktop Sidebar Navigation */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 z-30 flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 select-none">
        {/* Brand Logo Header */}
        <div className="h-16 px-6 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-blue-500/25">
              <ShieldCheck size={22} className="stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-slate-900 dark:text-white tracking-tight text-base leading-none">CodeQuality</span>
                <span className="text-[11px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 dark:bg-blue-900/50 dark:text-blue-300 border border-blue-200 dark:border-blue-700/60 leading-none">AI</span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 font-medium leading-tight mt-0.5">Defect Risk Predictor</p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="px-3 text-[11px] font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-2">
            Workspace
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 font-semibold shadow-sm shadow-blue-500/5'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100/80 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    size={18}
                    className={
                      isActive
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-slate-400 dark:text-slate-500'
                    }
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Cloned Repository Status Pill */}
        {scanResults && (
          <div className="px-4 py-3 mx-3 mb-3 bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-slate-800/60 dark:to-blue-950/20 rounded-xl border border-slate-200/80 dark:border-slate-700/60 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Active Analysis</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>
            <p className="font-semibold text-xs text-slate-800 dark:text-slate-200 truncate mt-1">
              {scanResults.repo_info?.name || 'Java Repository'}
            </p>
            <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">
              {scanResults.summary?.total_analyzed || 0} files • {scanResults.summary?.high_risk_count || 0} high risk
            </p>
          </div>
        )}

        {/* Footer & Theme Switcher */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700/60 transition"
            >
              {theme === 'dark' ? (
                <>
                  <Sun size={14} className="text-amber-400" />
                  <span>Light Mode</span>
                </>
              ) : (
                <>
                  <Moon size={14} className="text-slate-600" />
                  <span>Dark Mode</span>
                </>
              )}
            </button>
          </div>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
            title="GitHub"
          >
            <ExternalLink size={15} />
          </a>
        </div>
      </aside>
    </>
  );
};

export default Navigation;

