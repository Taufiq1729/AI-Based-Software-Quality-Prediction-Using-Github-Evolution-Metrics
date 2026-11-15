import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ScanProvider } from './context/ScanContext';
import Navigation from './components/Navigation';
import FileDetailModal from './components/FileDetailModal';
import Home from './pages/Home';
import LiveAnalysis from './pages/LiveAnalysis';
import Dashboard from './pages/Dashboard';
import FileExplorer from './pages/FileExplorer';
import ModelEvaluation from './pages/ModelEvaluation';
import Simulator from './pages/Simulator';
import About from './pages/About';

function App() {
  return (
    <ScanProvider>
      <Router>
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col lg:flex-row font-sans transition-colors duration-200">
          {/* Sidebar & Top Navigation */}
          <Navigation />

          {/* Main Content Area */}
          <main className="flex-1 lg:pl-64 min-h-screen flex flex-col">
            <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
              <Routes>
                {/* Primary CodeQuality AI Routes */}
                <Route path="/" element={<Home />} />
                <Route path="/analysis" element={<LiveAnalysis />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/files" element={<FileExplorer />} />
                <Route path="/models" element={<ModelEvaluation />} />
                <Route path="/simulator" element={<Simulator />} />
                <Route path="/about" element={<About />} />

                {/* Legacy / Alias Route Redirections */}
                <Route path="/scanner" element={<LiveAnalysis />} />
                <Route path="/predictor" element={<Simulator />} />
                <Route path="/analytics" element={<ModelEvaluation />} />
                <Route path="/how-it-works" element={<About />} />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </main>

          {/* Global Modal for File Detail & SHAP breakdown */}
          <FileDetailModal />
        </div>
      </Router>
    </ScanProvider>
  );
}

export default App;
