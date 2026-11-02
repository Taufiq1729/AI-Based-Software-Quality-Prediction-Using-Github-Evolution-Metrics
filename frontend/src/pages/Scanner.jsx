import { useMemo, useState } from 'react';
import axios from 'axios';
import { AlertCircle, ChevronDown, GitCommitHorizontal, LoaderCircle, Search } from 'lucide-react';
import {
  compareByPath,
  filterScanFiles,
  formatModelScore,
  getScore,
  hasValidScore,
  limitScanFiles,
  PAGE_LIMITS,
  sortScanFiles,
  SORT_OPTIONS,
} from './scannerUtils';
import './Scanner.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const FEATURE_ORDER = [
  'LOC', 'WMC', 'DIT', 'NOC', 'RFC', 'LCOM5', 'CBO', 'NPA', 'NPM', 'NLE', 'CBOI', 'CD',
  'code_churn', 'revision_count', 'developer_count',
];
const PREFERENCE_DEFAULTS = {
  showModelScore: false,
  search: '',
  sortBy: 'rank',
  topN: '20',
};

const readPreference = (key) => {
  try {
    const stored = window.localStorage.getItem(`sqam.scanner.${key}`);
    if (stored === null) return PREFERENCE_DEFAULTS[key];
    if (key === 'showModelScore') return stored === 'true';
    if (key === 'topN' && PAGE_LIMITS.includes(stored)) return stored;
    if (key === 'sortBy' && SORT_OPTIONS.includes(stored)) return stored;
    if (key === 'search') return stored;
  } catch (error) {
    console.warn(`Scanner preference "${key}" could not be restored.`, error);
  }
  return PREFERENCE_DEFAULTS[key];
};

const persistPreference = (key, value) => {
  try {
    window.localStorage.setItem(`sqam.scanner.${key}`, String(value));
  } catch (error) {
    console.warn(`Scanner preference "${key}" could not be saved.`, error);
  }
};

const formatNumber = (value) => (
  Number.isFinite(Number(value))
    ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 6 })
    : '—'
);

const getRelativePriority = (rank, total) => {
  if (rank === 1) return 'Highest priority';
  const position = (rank - 1) / Math.max(total - 1, 1);
  if (position <= 0.25) return 'High relative priority';
  if (position <= 0.75) return 'Medium relative priority';
  return 'Lower relative priority';
};

const getRepositoryName = (repositoryUrl) => {
  try {
    const segments = new URL(repositoryUrl).pathname.split('/').filter(Boolean);
    return segments.at(-1)?.replace(/\.git$/i, '') || repositoryUrl;
  } catch {
    return repositoryUrl;
  }
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || String(item)).join(', ');
  return 'The repository scan could not be completed. Confirm the API is available and the repository is accessible.';
};

const ScanSummary = ({ label, value, detail }) => (
  <div className="scan-summary-card">
    <span className="scan-summary-value">{formatNumber(value)}</span>
    <span className="scan-summary-label">{label}</span>
    {detail && <span className="scan-summary-detail">{detail}</span>}
  </div>
);

const DiagnosticList = ({ title, items, itemLabel }) => {
  if (!items?.length) return null;
  return (
    <details className="diagnostic-list">
      <summary>{title} ({items.length})</summary>
      <ul>
        {items.map((item, index) => {
          const file = item.file || item.path || item.class_identity || item.name;
          const reason = item.reason || item.error || item.message;
          return (
            <li key={`${file || itemLabel}-${index}`}>
              <span>{file || `${itemLabel} ${index + 1}`}</span>
              {reason && <span className="text-muted">{reason}</span>}
            </li>
          );
        })}
      </ul>
    </details>
  );
};

const FileResult = ({ file, showModelScore }) => (
  <article className="scan-file">
    <div className="scan-file-main">
      <span className="scan-rank" aria-label={`Rank ${file.rank}`}>#{file.rank}</span>
      <div className="scan-file-path">
        <strong>{String(file.file || '').split('/').at(-1)}</strong>
        <span className="text-muted scan-path-full">{file.file}</span>
        {file.class_identity && <span className="text-muted">{file.class_identity}</span>}
      </div>
      <div className={`priority-label priority-${file.priorityKey}`}>
        {file.priority}
        {file.score_tie_count > 1 && <small>Equal score; path order only</small>}
      </div>
      <div className="scan-file-metrics">
        <span><small>LOC</small><strong>{formatNumber(file.loc)}</strong></span>
        <span><small>Code churn</small><strong>{formatNumber(file.churn)}</strong></span>
        <span><small>Revisions</small><strong>{formatNumber(file.revisions)}</strong></span>
      </div>
      {showModelScore && (
        <div className="optional-score">
          <span>Predicted defect-proneness score</span>
          <strong>{formatModelScore(getScore(file))}</strong>
          <small>Uncalibrated model estimate, not a defect probability.</small>
        </div>
      )}
    </div>

    <details className="feature-details">
      <summary><ChevronDown size={16} aria-hidden="true" /> Inspect file and model details</summary>
      <div className="file-details">
        <span><strong>File path</strong>{file.file}</span>
        <span><strong>Primary class</strong>{file.class_identity || 'Identity not resolved'}</span>
        <span><strong>Developers</strong>{formatNumber(file.metrics?.developer_count)}</span>
        {showModelScore && (
          <span><strong>Raw model score</strong>{getScore(file).toFixed(8)}</span>
        )}
      </div>
      <h4 className="feature-detail-heading">Extracted features (15)</h4>
      <dl className="feature-grid">
        {FEATURE_ORDER.map((feature) => (
          <div className="feature-value" key={feature}>
            <dt>{feature}</dt>
            <dd>{formatNumber(file.metrics?.[feature])}</dd>
          </div>
        ))}
      </dl>
      <p className="feature-note">
        One primary file-level result is shown; nested and additional classes are not independently scored.
      </p>
    </details>
  </article>
);

const Scanner = () => {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [scan, setScan] = useState(null);
  const [error, setError] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [showModelScore, setShowModelScore] = useState(() => readPreference('showModelScore'));
  const [search, setSearch] = useState(() => readPreference('search'));
  const [sortBy, setSortBy] = useState(() => readPreference('sortBy'));
  const [topN, setTopN] = useState(() => readPreference('topN'));

  const rankedFiles = useMemo(() => {
    const validFiles = (scan?.files || []).filter(hasValidScore);
    const scoreSorted = [...validFiles].sort(
      (left, right) => getScore(right) - getScore(left) || compareByPath(left, right),
    );
    const total = Number(scan?.files_scored ?? scoreSorted.length);
    const firstRankByFile = new Map(
      scoreSorted.map((file, index) => [file, Number.isInteger(file.rank) ? file.rank : index + 1]),
    );

    return scoreSorted.map((file) => {
      const rank = firstRankByFile.get(file);
      const priority = file.priority || getRelativePriority(rank, total);
      const priorityKey = priority.startsWith('Highest')
        ? 'highest'
        : priority.startsWith('High')
          ? 'high'
          : priority.startsWith('Medium')
            ? 'medium'
            : 'lower';
      return { ...file, rank, priority, priorityKey };
    });
  }, [scan]);

  const searchedFiles = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return sortScanFiles(filterScanFiles(rankedFiles, query), sortBy);
  }, [rankedFiles, search, sortBy]);

  const displayedFiles = useMemo(() => (
    limitScanFiles(searchedFiles, topN)
  ), [searchedFiles, topN]);

  const updatePreference = (key, setter, value) => {
    setter(value);
    persistPreference(key, value);
  };

  const handleScan = async (event) => {
    event.preventDefault();
    setError('');
    setScan(null);
    setHasSubmitted(false);

    let parsedUrl;
    try {
      parsedUrl = new URL(repoUrl.trim());
    } catch {
      setError('Enter a complete GitHub repository URL, such as https://github.com/owner/repository.');
      return;
    }

    const pathSegments = parsedUrl.pathname.split('/').filter(Boolean);
    if (
      !['http:', 'https:'].includes(parsedUrl.protocol)
      || !['github.com', 'www.github.com'].includes(parsedUrl.hostname.toLowerCase())
      || pathSegments.length !== 2
    ) {
      setError('Enter a GitHub repository URL in the form https://github.com/owner/repository.');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/scan-repo?limit=0`,
        { url: parsedUrl.href },
      );
      setScan(response.data);
      setHasSubmitted(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  const discovered = scan?.java_files_discovered ?? 0;
  const analyzed = scan?.files_analyzed ?? scan?.total_java_files_analyzed ?? 0;
  const scored = scan?.files_scored ?? 0;
  const returned = scan?.files_returned ?? scan?.files?.length ?? 0;
  const notScored = Math.max(0, Number(analyzed) - Number(scored));
  const contextFailures = scan?.context_parse_failures || [];
  const analysisFailures = scan?.analysis_failures || [];
  const predictionFailures = scan?.prediction_failures || [];
  const unidentified = scan?.unidentified_class_files || [];

  return (
    <main className="scanner-page">
      <header className="scanner-header">
        <p className="eyebrow">Primary analysis workflow</p>
        <h1>Repository Scanner</h1>
        <p className="text-muted">
          Rank Java files by their model-estimated defect-proneness to prioritize manual inspection.
        </p>
      </header>

      <section className="scanner-form-panel">
        <form className="scanner-form" onSubmit={handleScan}>
          <label htmlFor="repository-url">Public GitHub repository URL</label>
          <div className="scanner-input-row">
            <input
              id="repository-url"
              type="url"
              inputMode="url"
              autoComplete="url"
              placeholder="https://github.com/owner/repository"
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              required
              disabled={loading}
            />
            <button type="submit" className="btn-primary scan-submit" disabled={loading}>
              {loading ? <LoaderCircle className="animate-spin" size={19} aria-hidden="true" /> : <Search size={19} aria-hidden="true" />}
              {loading ? 'Scanning repository' : 'Start repository scan'}
            </button>
          </div>
          <p className="text-muted scanner-help">
            The scan returns all scored Java files so you can search and filter the complete ranking. Evolution metrics depend on the Git history available in the clone.
          </p>
        </form>
      </section>

      {error && (
        <div className="scanner-error" role="alert">
          <AlertCircle size={20} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <section className="scan-progress" role="status" aria-live="polite">
          <LoaderCircle className="animate-spin" size={30} aria-hidden="true" />
          <div>
            <strong>Scan request in progress</strong>
            <p className="text-muted">
              The API is cloning the repository, extracting source and Git metrics, and scoring file-level results.
              Stage-by-stage progress is not streamed by the current API.
            </p>
          </div>
        </section>
      )}

      {hasSubmitted && scan && (
        <section className="scan-results" aria-live="polite">
          <div className="scan-result-heading">
            <div>
              <p className="eyebrow">Scan complete</p>
              <h2>{getRepositoryName(scan.repository || repoUrl)}</h2>
              <p className="scan-commit">
                <GitCommitHorizontal size={17} aria-hidden="true" />
                Commit
                <code title={scan.repository_commit || 'Commit identifier unavailable'}>
                  {scan.repository_commit || 'Unavailable'}
                </code>
              </p>
            </div>
            <span className="scan-model-tag">Combined Logistic Regression · 15 features</span>
          </div>

          <div className="scan-summary-grid">
            <ScanSummary label="Java files discovered" value={discovered} />
            <ScanSummary label="Files analyzed" value={analyzed} detail="Feature extraction completed" />
            <ScanSummary label="Files successfully scored" value={scored} />
            <ScanSummary label="Files returned by API" value={returned} detail={scan.result_limit ? `Top ${scan.result_limit}` : 'Complete scored result set'} />
          </div>

          <div className="scan-diagnostics">
            <div className="diagnostics-title">
              <h3>Scan diagnostics</h3>
              <p className="text-muted">Files without scores were excluded from the ranking; no missing score is inferred.</p>
            </div>
            <div className="diagnostics-counts">
              <span><strong>{notScored}</strong> analyzed files not scored</span>
              <span><strong>{contextFailures.length}</strong> context parse failures</span>
              <span><strong>{analysisFailures.length}</strong> file analysis failures</span>
              <span><strong>{predictionFailures.length}</strong> invalid or failed predictions</span>
              <span><strong>{unidentified.length}</strong> files without resolved identity</span>
              <span><strong>{formatNumber(scan.unresolved_project_references ?? 0)}</strong> unresolved project references</span>
              <span><strong>{formatNumber(scan.non_primary_classes_not_scored ?? 0)}</strong> additional declarations not scored</span>
            </div>
            <div className="diagnostic-details">
              <DiagnosticList title="Context parse failures" items={contextFailures} itemLabel="Parser failure" />
              <DiagnosticList title="File analysis failures" items={analysisFailures} itemLabel="Analysis failure" />
              <DiagnosticList title="Prediction failures" items={predictionFailures} itemLabel="Prediction failure" />
              <DiagnosticList title="Unidentified class files" items={unidentified} itemLabel="Unidentified file" />
            </div>
            <p className="text-muted primary-class-note">
              Each Java file has at most one primary file-level prediction. Additional and nested class declarations do not receive independent scores.
            </p>
          </div>

          {rankedFiles.length > 0 && (
            <section className="ranking-controls" aria-label="Ranking controls">
              <div className="ranking-controls-heading">
                <div>
                  <h3>Ranked Java files</h3>
                  <p className="text-muted">Rank is determined by the class-1 model score, highest first. Equal scores are ordered alphabetically by file path and share the same priority tier.</p>
                </div>
                <label className="score-toggle">
                  <input
                    type="checkbox"
                    checked={showModelScore}
                    onChange={(event) => updatePreference('showModelScore', setShowModelScore, event.target.checked)}
                  />
                  <span className="toggle-track" aria-hidden="true" />
                  <span>Show model score</span>
                </label>
              </div>

              <div className="ranking-toolbar">
                <label className="ranking-search">
                  <Search size={17} aria-hidden="true" />
                  <span className="sr-only">Search Java file name or path</span>
                  <input
                    type="search"
                    placeholder="Search file name or path"
                    value={search}
                    onChange={(event) => updatePreference('search', setSearch, event.target.value)}
                  />
                </label>
                <label className="ranking-select">
                  <span>Sort by</span>
                  <select
                    value={sortBy}
                    onChange={(event) => updatePreference('sortBy', setSortBy, event.target.value)}
                  >
                    <option value="rank">Rank (highest score first)</option>
                    <option value="file">File name / path</option>
                    <option value="score">Model score</option>
                    <option value="LOC">LOC</option>
                    <option value="code_churn">Code churn</option>
                    <option value="revision_count">Revision count</option>
                  </select>
                </label>
                <label className="ranking-select">
                  <span>Show</span>
                  <select
                    value={topN}
                    onChange={(event) => updatePreference('topN', setTopN, event.target.value)}
                  >
                    <option value="10">Top 10</option>
                    <option value="20">Top 20</option>
                    <option value="50">Top 50</option>
                    <option value="all">All matching</option>
                  </select>
                </label>
              </div>

              <p className="ranking-count" aria-live="polite">
                Showing <strong>{formatNumber(displayedFiles.length)}</strong> of{' '}
                <strong>{formatNumber(searchedFiles.length)}</strong> matching files ·{' '}
                {formatNumber(scored)} files scored in total
                {search.trim() && ` · ${formatNumber(rankedFiles.length)} scored files in this scan`}
              </p>
              {returned < scored && (
                <p className="scanner-warning">
                  The API returned {formatNumber(returned)} of {formatNumber(scored)} scored files; this is a partial ranking.
                </p>
              )}
              {scan.ranking_tie_breaker && <p className="ranking-tie-note">{scan.ranking_tie_breaker}</p>}
              {scan.priority_rule && <p className="ranking-priority-note">{scan.priority_rule}</p>}

              {displayedFiles.length > 0 ? (
                <div className="scan-file-list">
                  {displayedFiles.map((file) => (
                    <FileResult
                      file={file}
                      showModelScore={showModelScore}
                      key={`${file.file}-${file.rank}`}
                    />
                  ))}
                </div>
              ) : (
                <div className="scanner-empty">
                  <h3>No matching Java files</h3>
                  <p className="text-muted">Try another file name or path, or clear the search.</p>
                </div>
              )}
            </section>
          )}

          {rankedFiles.length === 0 && (
            <div className="scanner-empty">
              <h3>No Java files were successfully scored</h3>
              <p className="text-muted">
                {scan.message || 'The repository had no supported Java files, or extraction and prediction did not produce any valid file scores.'}
              </p>
            </div>
          )}

          <p className="score-disclaimer">
            Model scores rank components for inspection; they are uncalibrated estimates, not verified
            defect probabilities. These scores represent the model&apos;s estimates based on source-code
            metrics and Git history. They help prioritize manual inspection and do not confirm the
            presence of defects.
          </p>
        </section>
      )}
    </main>
  );
};

export default Scanner;
