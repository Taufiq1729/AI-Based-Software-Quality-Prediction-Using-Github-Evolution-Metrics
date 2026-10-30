# Final Validation Audit: Java Defect Prediction Pipeline

**Audit date:** 2026-10-30  
**Scope:** Java-only historical JUnit 4 pipeline. The package-qualified identity correction was applied to DIT/NOC/CBOI, all releases were regenerated, and models were retrained without changing raw data, labels, feature order, or the chronological split.

## Executive Summary

The implementation is reproducible at the feature and artifact level, but it is **not ready for unqualified paper claims about predictive reliability**.

- All 12,244 retained class records were reanalyzed at their exact historical commits. All 12 static features match the regenerated rows within `1e-9`, with zero tolerance mismatches and zero parser/analysis failures.
- Package/enclosing-type identities now drive inheritance and inward-coupling resolution. The full audit identifies 10,407 named records and 1,837 anonymous/synthetic records; ambiguous and unresolved named relationships are reported rather than merged by simple name.
- DIT changed for 301 records, NOC for 272, and CBOI for 9,657. The other nine static features remained exactly unchanged. All 12,244 record IDs and original labels are preserved.
- Native Git history matched ordinary, renamed/moved, multi-contributor, deleted-file, long-history, and future-exclusion fixtures, plus one actual generated file in each of the 12 releases.
- The held-out set contains 25 positives (0.97%); the 2020 release has none. Combined Logistic Regression is strongest by AP (0.0276) and ROC-AUC (0.7890), but precision remains 0.0244. The majority baseline has higher accuracy (0.9903) than every model.
- `PR_AUC` now means scikit-learn average precision. Trapezoidal PR area is separately named; for the constant majority baseline it is 0.50486 despite zero recall, while AP is 0.00972.

**Verdict:** the identity correction and experiment are reproducible, but results are **not sufficient for unqualified paper claims of predictive superiority or deployment readiness**. The test population is extremely imbalanced and the newest release has no positive examples. Anonymous-class records have no stable source-level FQCN; unresolved project/library symbols are documented and excluded from project relationships.

## Static Metric Parity

The audit checked every retained row in all 12 regenerated release files. For every release, it verified the checked-out `HEAD` equals the dataset commit, built the repository context at that checkout, then invoked the same class name, line range, source path, and context inputs used by the regeneration path. The row was joined to the original CSV by `ID`.

There were 12,244 comparisons for each feature. Exact match means zero absolute floating-point difference after CSV round-trip. The tolerance comparison uses `1e-9`.

| Feature | Exact matches | Exact rate | MAE | Maximum absolute error | Mismatches > 1e-9 or failed |
|---|---:|---:|---:|---:|---:|
| LOC | 12,244 | 100.0000% | 0 | 0 | 0 |
| WMC | 12,244 | 100.0000% | 0 | 0 | 0 |
| DIT | 12,244 | 100.0000% | 0 | 0 | 0 |
| NOC | 12,244 | 100.0000% | 0 | 0 | 0 |
| RFC | 12,244 | 100.0000% | 0 | 0 | 0 |
| LCOM5 | 12,083 | 98.6851% | 1.387609e-18 | 2.220446e-16 | 0 |
| CBO | 12,244 | 100.0000% | 0 | 0 | 0 |
| NPA | 12,244 | 100.0000% | 0 | 0 | 0 |
| NPM | 12,244 | 100.0000% | 0 | 0 | 0 |
| NLE | 12,244 | 100.0000% | 0 | 0 | 0 |
| CBOI | 12,244 | 100.0000% | 0 | 0 | 0 |
| CD | 10,988 | 89.7419% | 4.555456e-18 | 9.714451e-17 | 0 |

The non-bitwise differences in `LCOM5` and `CD` are floating-point roundoff only; every row is within tolerance. The retained class files all parsed with the AST path: 12,244 AST parses, zero regex fallbacks, zero parser errors, zero missing-source rows, zero same-file duplicate-name matches, zero ambiguous near-line candidates, and zero line/name conflicts.

**Qualified identity results:** 10,407 retained rows resolve to one package/enclosing-type identity; 1,837 rows use anonymous/synthetic `$n` names with no source-level `TypeDeclaration` identity and are explicitly categorized rather than treated as unresolved named classes. No named row remains unresolved in the regenerated release set. Cross-package duplicate simple names no longer share NOC/CBOI keys. The context resolver handles same-package, explicit import, unambiguous wildcard import, nested, and fully-qualified references. Ambiguous wildcard or absent project symbols are written to per-release `identity_context_<commit>.json` and do not produce project edges. Across the 12 contexts, 13,116 non-project/ambiguous references and 4,696 external/standard references were recorded; external library definitions are not resolved without classpath data. This can undercount dependencies and inheritance outside the checked-out project.

**Before/after identity features:** DIT changed on 301 records (MAE 0.03324, max change 4); NOC changed on 272 (MAE 0.04206, max 4); CBOI changed on 9,657 (MAE 2.15518, max 78). LOC, WMC, RFC, LCOM5, CBO, NPA, NPM, NLE, and CD each changed on zero rows. The raw datasets were not modified.

**Nested/anonymous mapping:** benchmark `$` nested names are resolved to enclosing-type identities for relationship metrics while the established line-based selection for other static metrics remains unchanged. Anonymous `$1` rows cannot receive a stable named FQCN; the analyzer reports them as synthetic and does not invent a project identity.

**Parser boundary:** no unsupported construct was encountered in any source file referenced by a retained row. The installed `javalang 0.13.0` accepted the tested local `var` syntax, but rejected module declarations, records, text blocks, sealed classes, pattern-matching `instanceof`, and switch expressions. Unsupported input falls back to approximate regex metrics in the current analyzer; the audit records such fallback per row rather than counting it as a successful AST parse. These probes are in `data/audit/parser_construct_probes.json`.

## Git Evolution Metric Validation

The independent reference used native `git log --follow -M --numstat` and commit author identities. It defines churn as the sum of additions and deletions over the file history through the requested commit, revisions as commits returned for the followed path, and developers as distinct author email (falling back to author name).

| Scenario | code_churn | revision_count | developer_count | Result |
|---|---:|---:|---:|---|
| Ordinary file at historical cutoff | 4 | 2 | 2 | Exact match |
| Ordinary file after later edit | 5 | 3 | 3 | Exact match |
| Rename and move across directories at release | 5 | 3 | 3 | Exact match |
| Moved file after future edit | 6 | 4 | 4 | Exact match |
| Historical cutoff excludes future edit | 5 vs. 6 | 3 vs. 4 | 3 vs. 4 | Verified |
| Deleted file through deletion commit | 8 | 3 | 3 | Exact match |
| Long-history file (13 revisions) | 15 | 13 | 5 | Exact match |
| Repository miner vs. per-file miner | 5 | 3 | 3 | Exact match |

All three metrics also matched the saved derived values for one unique source file in each of the 12 actual release commits. All 21 recorded scenarios passed with zero metric discrepancies. The independent release checks are samples, not exhaustive native re-mining of every unique file path in all 12 snapshots; the exhaustive portion here is static-feature parity.

Rename behavior is consistent for Git-detectable renames/moves. As with native Git, similarity detection can fail for a heavily rewritten or unrelated replacement file. Developer counts identify Git author metadata, not necessarily distinct human beings; aliases are not canonicalized.

## Temporal and Label Validation

The 12 release commits are strictly ordered by committer date. Training and test commit lists are disjoint, and the latest training release precedes the earliest test release. All retained labels match their original raw dataset labels by `ID` (12,244/12,244). `isDefective` is absent from the 15-feature schema. The rebuild reads the defect value only to copy it to the output row after feature extraction; no label is passed into static analysis or Git mining.

One raw row is excluded and recorded in `data/derived/junit4_regenerated/unmapped_records.json`: ID `L119`, release `r4.11-beta-1` (`88c28a42a6fb7dc462c4bc504189a76a815fc265`), class `JunitDependencyTest`. Its CSV path points to a generated Maven sample-project file absent from that historical commit. It is non-defective; excluding it changes neither the positive-label total nor the train/test split.

| Release | Commit | Commit date | Partition | Total | Defective | Non-defective | Defect % |
|---|---|---|---|---:|---:|---:|---:|
| r4.8 | `5a3a326096cf65a58272ee89a5ef1c164cfd9d33` | 2009-11-30 | Train | 654 | 17 | 637 | 2.5994% |
| r4.8.2 | `a30e87b6ac67f14a42b97d427bb1c8c6ba18cd87` | 2010-04-08 | Unused | 657 | 24 | 633 | 3.6530% |
| r4.9b1 | `751f75986b11336ac8310d73c89003b0b09ecb92` | 2011-01-03 | Unused | 699 | 47 | 652 | 6.7239% |
| r4.9b3 | `5a9eb89e15ca86a3db6a4e21f5c9f94f9ab8fb60` | 2011-07-06 | Unused | 724 | 51 | 673 | 7.0442% |
| r4.9 | `61f06547599bb6b98bca99d5bc457eb20bc17cab` | 2011-08-22 | Train | 731 | 62 | 669 | 8.4815% |
| r4.11-beta-1 | `88c28a42a6fb7dc462c4bc504189a76a815fc265` | 2012-10-15 | Train | 866 | 22 | 844 | 2.5404% |
| r4.12-beta-1 | `0550afa689cc5c7860d4378b27ecd38d35c05570` | 2014-07-27 | Unused | 1,110 | 0 | 1,110 | 0.0000% |
| r4.12 | `64155f8a9babcfcf4263cf4d08253a1556e75481` | 2014-12-04 | Test | 1,154 | 25 | 1,129 | 2.1664% |
| r4.13-beta-1 | `6e1d2e6ebbc484af60c06bd26cc55349b352e49e` | 2018-11-25 | Unused | 1,405 | 7 | 1,398 | 0.4982% |
| r4.13-beta-3 | `fc3813fba9e2250ddd96877d01f2f694127edb80` | 2019-05-05 | Unused | 1,414 | 7 | 1,407 | 0.4950% |
| r4.13-rc-1 | `17d340a7d2661f0a0c7e284b49cd70f5a4495d6b` | 2019-10-26 | Unused | 1,412 | 2 | 1,410 | 0.1416% |
| r4.13.1 | `1b683f4ec07bcfa40149f086d32240f805487e66` | 2020-10-11 | Test | 1,418 | 0 | 1,418 | 0.0000% |

The training prevalence is 101/2,251 = **4.4869%**: it combines r4.8 at 2.60%, r4.9 at 8.48%, and r4.11-beta-1 at 2.54%. Test prevalence is 25/2,572 = **0.9720%**: r4.12 contributes 25/1,154 (2.17%), and r4.13.1 contributes 0/1,418. This is release-composition and temporal label-prevalence shift, not a preprocessing change: record labels match the source labels. The test release with no positives limits performance interpretation.

## Model Evaluation

All six models were retrained after the identity-feature update, without using the held-out test releases during tuning. The saved metrics were independently recomputed from each saved model and the final test matrix; every metric and confusion matrix matched exactly. `PR_AUC` is average precision (`average_precision_score`); trapezoidal area is separately reported.

| Model | Features | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC | AP (`PR_AUC`) | Trapezoidal PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | Static | 0.6967 | 0.6092 | 0.0166 | 0.5200 | 0.0323 | 0.6892 | 0.0203 | 0.0179 |
| Logistic Regression | Combined | 0.7784 | 0.6703 | 0.0244 | 0.5600 | 0.0468 | 0.7890 | 0.0276 | 0.0252 |
| Decision Tree | Static | 0.9184 | 0.4637 | 0.0000 | 0.0000 | 0.0000 | 0.4637 | 0.0097 | 0.0049 |
| Decision Tree | Combined | 0.9825 | 0.5159 | 0.0455 | 0.0400 | 0.0426 | 0.5159 | 0.0114 | 0.0475 |
| Random Forest | Static | 0.9257 | 0.4674 | 0.0000 | 0.0000 | 0.0000 | 0.5531 | 0.0104 | 0.0098 |
| Random Forest | Combined | 0.9759 | 0.4927 | 0.0000 | 0.0000 | 0.0000 | 0.6535 | 0.0160 | 0.0149 |
| Majority-class baseline | None | 0.9903 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.0097 | 0.5049 |

Confusion matrices use `[[TN, FP], [FN, TP]]`:

| Model | Features | Confusion matrix |
|---|---|---|
| Logistic Regression | Static | `[[1779, 768], [12, 13]]` |
| Logistic Regression | Combined | `[[1988, 559], [11, 14]]` |
| Decision Tree | Static | `[[2362, 185], [25, 0]]` |
| Decision Tree | Combined | `[[2526, 21], [24, 1]]` |
| Random Forest | Static | `[[2381, 166], [25, 0]]` |
| Random Forest | Combined | `[[2510, 37], [25, 0]]` |
| Majority-class baseline | None | `[[2547, 0], [25, 0]]` |

At the default model decision rule, the six positive prediction counts are 781, 573, 185, 22, 166, and 37, respectively; the majority baseline predicts zero positives. Both Random Forest variants have zero true positives. Their maximum scores among actual defects are 0.3810 (static) and 0.3840 (combined), while their 95th-percentile defect scores are 0.3577 and 0.3669. Thus all actual defects are below the classifier threshold even though some negative examples score above it. This is poor class separation under this temporal/prevalence shift, not a threshold chosen from test labels. No threshold tuning is implemented.

**Per-release test results:**

| Release | N | Defects | Model | Features | Accuracy | AP | ROC-AUC | Predicted positive | Confusion matrix |
|---|---:|---:|---|---|---:|---:|---:|---:|---|
| r4.12 | 1,154 | 25 | Logistic Regression | Static | 0.6976 | 0.0470 | 0.6949 | 350 | `[[792,337],[12,13]]` |
| r4.12 | 1,154 | 25 | Logistic Regression | Combined | 0.7990 | 0.0685 | 0.8057 | 235 | `[[908,221],[11,14]]` |
| r4.12 | 1,154 | 25 | Decision Tree | Static | 0.9090 | 0.0217 | 0.4646 | 80 | `[[1049,80],[25,0]]` |
| r4.12 | 1,154 | 25 | Decision Tree | Combined | 0.9688 | 0.0244 | 0.5147 | 13 | `[[1117,12],[24,1]]` |
| r4.12 | 1,154 | 25 | Random Forest | Static | 0.9090 | 0.0229 | 0.5512 | 80 | `[[1049,80],[25,0]]` |
| r4.12 | 1,154 | 25 | Random Forest | Combined | 0.9593 | 0.0347 | 0.6574 | 22 | `[[1107,22],[25,0]]` |
| r4.13.1 | 1,418 | 0 | All models | All | Ranking metrics undefined | N/A | N/A | See saved JSON | No positive class |

Per-release score quantiles by true class, counts, and full confusion matrices are retained in `data/results/evaluation_metrics.json`. ROC-AUC, AP, and PR curves are undefined for r4.13.1 because it has no positive labels. Its 100% majority-baseline accuracy is not evidence of defect detection.

## Reproducibility Checks

- A clean regeneration uses: `python src/data/rebuild_static_metrics.py`, `python src/data/preprocessing.py`, `python src/models/train.py`, `python src/models/evaluate.py`, and `python src/models/explain.py`. `python src/data/rebuild_identity_metrics.py` is the staged, before/after-only command used to recalculate DIT/NOC/CBOI while preserving the original regenerated snapshot.
- Feature order is the shared 15-column contract. Saved imputer keys and scaler feature names match it; all six model artifacts load.
- Applying the persisted medians and scaler to raw test-release features reproduces `X_test.csv` with maximum absolute difference `3.552714e-15`.
- Model constructors use `random_state=42`; the SHAP sample uses `random_state=42`. Saved evaluation outputs exactly match recalculation from the saved model/test data.
- Regenerating feature importance and SHAP artifacts produced identical SHA-256 hashes for all four outputs.
- Random Forest tuning uses expanding-window CV that holds out whole training releases. The held-out test releases are not used in fitting or threshold selection.
- `PR_AUC` is `average_precision_score`; `PR_AUC_trapezoidal` remains separate. Threshold selection is not implemented and no threshold was chosen using test labels.
- Python dependencies are not version-pinned in `requirements.txt`; serialized scikit-learn models and floating-point outputs may not be portable across dependency versions. Pin a tested environment for external reproduction.
- Dataset acquisition and historical Git mirror availability remain external prerequisites. This audit reused the checked-in raw CSVs and local Git mirror.

## Audit Outputs

The audit runner is `src/data/final_validation_audit.py`; it resumes completed static releases after validating source/output hashes. The main outputs are:

- `data/audit/static/static_feature_summary.csv`: per-feature parity, MAE, maximum error, and mismatch counts.
- `data/audit/static/static_records_all_releases.csv`: full per-record comparisons and parser/mapping evidence.
- `data/audit/static/static_mismatches.csv`: all tolerance failures (empty for this run).
- `data/audit/static/static_mapping_parser_findings.csv`: parser, line-mapping, and duplicate-name findings.
- `data/audit/static/duplicate_simple_name_records.csv` and `duplicate_simple_name_groups.csv`: simple-name collision inventory.
- `data/audit/static/static_release_summary.csv`: release-level static audit counts.
- `data/audit/identity_fix/before_after_identity_features.csv`, `identity_feature_change_summary.csv`, and `identity_rebuild_manifest.json`: per-ID feature deltas, no-change checks, label checks, resolved/unresolved context diagnostics, and promotion record.
- `data/derived/junit4_regenerated/identity_context_<commit>.json`: exact per-release parse failures, duplicate FQCNs, and unresolved/external relationship references.
- `data/audit/git_evolution/git_evolution_fixture_audit.csv`: native Git fixture and 12 release-sample comparisons.
- `data/audit/dataset/release_distribution.csv` and `dataset_temporal_audit.json`: full release table, labels, and temporal checks.
- `data/audit/models/model_evaluation_audit.csv` and `model_reproducibility_audit.json`: saved-model recomputation, baseline, preprocessing, and explanation hashes.
- `data/audit/parser_construct_probes.json` and `audit_run_summary.json`: parser probes and consolidated audit status.

## Remaining Limitations and Readiness

The parity result proves that regenerated values and the authoritative analyzer agree; it does not prove every feature definition is a complete representation of software quality. Anonymous `$n` classes have no source-level identity and are not linked to speculative project relationships. The resolver does not have external classpath artifacts: non-project symbols remain unresolved/external and are excluded from project-level NOC/CBOI edges. Some unresolved references can therefore undercount dependencies. Java grammar outside the tested releases can also trigger approximate regex fallback. The Git checks include synthetic edge-case fixtures plus 12 real release samples, not exhaustive independent native re-mining of every file/release pair.

The test population has only 25 positive rows, all from r4.12; r4.13.1 has no positive labels. Every model has lower accuracy than the majority baseline, and combined Logistic Regression's AP is only 0.0276. These findings do not support generalization or model-superiority claims. More releases/projects and a test design with adequate positive cases are required before final paper claims.

**Final readiness verdict: implementation correction and reproducibility checks pass; predictive research readiness remains insufficient.** Package-qualified named identities removed the simple-name merge problem, but anonymous classes and external classpath resolution remain limitations. The extreme test imbalance and zero-positive latest release prevent strong predictive claims. Treat these model results as exploratory until evaluated on additional temporal releases with sufficient defects.