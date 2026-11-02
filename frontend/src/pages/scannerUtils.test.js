import assert from 'node:assert/strict';
import test from 'node:test';
import {
  filterScanFiles,
  formatModelScore,
  hasValidScore,
  limitScanFiles,
  sortScanFiles,
} from './scannerUtils.js';

const makeFile = (file, rank, modelScore, metrics = {}) => ({
  file,
  rank,
  model_score: modelScore,
  loc: metrics.loc ?? 10,
  churn: metrics.churn ?? 1,
  revisions: metrics.revisions ?? 1,
});

test('filters files by name, path, and class identity', () => {
  const files = [
    { ...makeFile('src/http/Client.java', 1, 0.8), class_identity: 'org.example.Client' },
    { ...makeFile('src/store/Database.java', 2, 0.5), class_identity: 'org.example.Repository' },
  ];

  assert.deepEqual(filterScanFiles(files, 'client'), [files[0]]);
  assert.deepEqual(filterScanFiles(files, 'src/store'), [files[1]]);
  assert.deepEqual(filterScanFiles(files, 'org.example.Repository'), [files[1]]);
  assert.equal(filterScanFiles(files, 'not-found').length, 0);
});

test('sorts by rank, name, model score, and other supported metrics', () => {
  const files = [
    makeFile('z/File.java', 2, 0.7, { loc: 20, churn: 5, revisions: 3 }),
    makeFile('a/File.java', 1, 0.9, { loc: 10, churn: 8, revisions: 1 }),
    makeFile('m/File.java', 3, 0.7, { loc: 30, churn: 2, revisions: 9 }),
  ];

  assert.deepEqual(sortScanFiles(files, 'rank').map((file) => file.rank), [1, 2, 3]);
  assert.deepEqual(sortScanFiles(files, 'file').map((file) => file.file), ['a/File.java', 'm/File.java', 'z/File.java']);
  assert.deepEqual(sortScanFiles(files, 'score').map((file) => file.file), ['a/File.java', 'm/File.java', 'z/File.java']);
  assert.deepEqual(sortScanFiles(files, 'LOC').map((file) => file.loc), [30, 20, 10]);
  assert.deepEqual(sortScanFiles(files, 'code_churn').map((file) => file.churn), [8, 5, 2]);
  assert.deepEqual(sortScanFiles(files, 'revision_count').map((file) => file.revisions), [9, 3, 1]);
});

test('Top 10, Top 20, Top 50, and All limit the filtered list', () => {
  const files = Array.from({ length: 60 }, (_, index) => makeFile(`src/${index}.java`, index + 1, 0.9 - index / 100));

  assert.equal(limitScanFiles(files, '10').length, 10);
  assert.equal(limitScanFiles(files, '20').length, 20);
  assert.equal(limitScanFiles(files, '50').length, 50);
  assert.equal(limitScanFiles(files, 'all').length, 60);
});

test('invalid or missing scores are excluded and model-score formatting is explicit', () => {
  assert.equal(hasValidScore(makeFile('valid.java', 1, 0)), true);
  assert.equal(hasValidScore({ file: 'missing.java' }), false);
  assert.equal(hasValidScore(makeFile('nan.java', 2, Number.NaN)), false);
  assert.equal(hasValidScore(makeFile('out-of-range.java', 3, 1.01)), false);
  assert.equal(formatModelScore(0.8732), '87.32% (model score: 0.8732)');
});
