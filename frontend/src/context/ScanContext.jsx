import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const ScanContext = createContext(null);

export const useScan = () => {
  const context = useContext(ScanContext);
  if (!context) {
    throw new Error('useScan must be used within a ScanProvider');
  }
  return context;
};

const API_BASE = 'http://localhost:8000';

export const ScanProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  const [currentTaskId, setCurrentTaskId] = useState(() => {
    return localStorage.getItem('currentTaskId') || null;
  });

  const [scanResults, setScanResults] = useState(null);
  const [loadingResults, setLoadingResults] = useState(false);
  const [selectedModel, setSelectedModel] = useState('LogisticRegression_combined');
  const [threshold, setThreshold] = useState(0.5);
  const [selectedFileForModal, setSelectedFileForModal] = useState(null);

  // Apply dark mode class to html element
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Persist currentTaskId
  useEffect(() => {
    if (currentTaskId) {
      localStorage.setItem('currentTaskId', currentTaskId);
      fetchScanResults(currentTaskId, selectedModel, threshold);
    }
  }, [currentTaskId]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  const fetchScanResults = async (taskId, model = selectedModel, thresh = threshold) => {
    if (!taskId) return;
    setLoadingResults(true);
    try {
      const response = await axios.get(`${API_BASE}/api/scan-results/${taskId}`, {
        params: { model, threshold: thresh }
      });
      if (response.data.status === 'completed') {
        setScanResults(response.data);
      }
    } catch (err) {
      console.error('Error fetching scan results:', err);
    } finally {
      setLoadingResults(false);
    }
  };

  const updateModelOrThreshold = async (newModel, newThreshold) => {
    const m = newModel !== undefined ? newModel : selectedModel;
    const t = newThreshold !== undefined ? newThreshold : threshold;
    setSelectedModel(m);
    setThreshold(t);

    if (currentTaskId) {
      await fetchScanResults(currentTaskId, m, t);
    }
  };

  return (
    <ScanContext.Provider
      value={{
        theme,
        toggleTheme,
        currentTaskId,
        setCurrentTaskId,
        scanResults,
        setScanResults,
        loadingResults,
        selectedModel,
        setSelectedModel,
        threshold,
        setThreshold,
        updateModelOrThreshold,
        fetchScanResults,
        selectedFileForModal,
        setSelectedFileForModal,
        apiBase: API_BASE
      }}
    >
      {children}
    </ScanContext.Provider>
  );
};

