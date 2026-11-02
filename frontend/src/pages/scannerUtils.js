export const SORT_OPTIONS = ['rank', 'file', 'score', 'LOC', 'code_churn', 'revision_count'];
export const PAGE_LIMITS = ['10', '20', '50', 'all'];

export const getScore = (file) => {
  const score = file?.model_score ?? file?.risk_probability;
  return score === null || score === undefined || score === '' ? Number.NaN : Number(score);
};

export const hasValidScore = (file) => (
  Number.isFinite(getScore(file)) && getScore(file) >= 0 && getScore(file) <= 1
);

export const formatModelScore = (score) => (
  `${(Number(score) * 100).toFixed(2)}% (model score: ${Number(score).toFixed(4)})`
);

export const compareByPath = (left, right) => (
  String(left.file || '').localeCompare(String(right.file || ''), undefined, { sensitivity: 'base' })
  || String(left.file || '').localeCompare(String(right.file || ''))
);

export const sortScanFiles = (files, sortBy) => [...files].sort((left, right) => {
  if (sortBy === 'file') return compareByPath(left, right) || left.rank - right.rank;
  if (sortBy === 'score') return getScore(right) - getScore(left) || compareByPath(left, right);
  if (sortBy === 'LOC') return Number(right.loc) - Number(left.loc) || left.rank - right.rank;
  if (sortBy === 'code_churn') return Number(right.churn) - Number(left.churn) || left.rank - right.rank;
  if (sortBy === 'revision_count') return Number(right.revisions) - Number(left.revisions) || left.rank - right.rank;
  return left.rank - right.rank;
});

export const filterScanFiles = (files, query) => {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return [...files];
  return files.filter((file) => [
    file.file, file.class_name, file.class_identity,
  ].some((value) => String(value || '').toLocaleLowerCase().includes(normalizedQuery)));
};

export const limitScanFiles = (files, topN) => (
  topN === 'all' ? [...files] : files.slice(0, Number(topN))
);
