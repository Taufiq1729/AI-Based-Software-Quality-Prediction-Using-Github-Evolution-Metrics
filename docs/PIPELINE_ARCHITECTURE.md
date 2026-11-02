# Java Quality Prediction Pipeline Architecture & Validation Document

## 1. Overview & Problem Addressed

### Previous Limitations
1. **Synthetic Git Evolution Metrics during Training**: The previous `preprocessing.py` contained `add_mock_evolution_metrics()`, which artificially fabricated `code_churn`, `revision_count`, and `developer_count` using random distributions conditioned on the target variable (`isDefective`), introducing both synthetic data and severe target leakage.
2. **Hardcoded Static Metrics during Repository Scanning**: The previous `/scan-repo` endpoint in `api/main.py` hardcoded placeholder values (`DIT=2, NOC=0, CBO=12, RFC=25, LCOM5=0.4, NPA=0, NPM=5, NLE=1, CBOI=3, CD=0.2`).
3. **Training / Serving Skew**: The metrics extracted during repository scanning did not use the same algorithms or definitions as the training dataset.

### Corrected Implementation
1. **Release-aligned Git history**: The pipeline mines native Git history for each release through its exact commit and follows detected renames/moves, preventing future-history lookahead.
2. **Java AST analysis**: `src/analyzers/java_analyzer.py` parses Java source using `javalang` and computes the declared static metric contract.
3. **Qualified project identity**: Project type declarations use package and enclosing-type identity. Same-package, explicit-import, wildcard-import, and qualified references are resolved conservatively; ambiguous or unresolved names are reported and excluded from project-level NOC/CBOI edges. Anonymous-class dataset names remain synthetic and have no source-level FQCN.
4. **Authoritative unified feature extractor**: `src/data/feature_extractor.py` provides the 15-feature schema, ordering, extraction, and validation shared by training and repository scanning.
5. **Chronological preprocessing**: JUnit 4.8, 4.9, and 4.11 are training releases; JUnit 4.12 and 4.13.1 are held-out test releases. Imputation medians and `StandardScaler` are fitted only on training data. Random Forest tuning uses expanding-window folds that hold out complete releases.
6. **Model training and evaluation**: Logistic Regression, Decision Tree, and Random Forest are trained with static-only and combined features. Average precision is the primary PR ranking measure; trapezoidal PR area is separately reported.

---

## 2. Authoritative 15 Feature Definitions

| Metric | Category | Extraction Mechanism & Definition |
|---|---|---|
| **LOC** | Static | Physical lines of code in the Java source file. |
| **WMC** | Static | Weighted Methods per Class: sum of McCabe Cyclomatic Complexity across all methods in the class ($1 + \text{branching points: if, while, for, do, catch, case, ternary, \&\&, \|\|}$). |
| **DIT** | Static | Depth of Inheritance Tree: length of inheritance chain from base class (project hierarchy traversal). |
| **NOC** | Static | Number of Children: number of immediate subclasses extending this class within the repository. |
| **RFC** | Static | Response for a Class: number of methods defined in class + distinct external methods invoked by methods in class. |
| **LCOM5** | Static | Henderson-Sellers Lack of Cohesion of Methods: $(m - \frac{1}{a} \sum_{i=1}^a m(a_i)) / (m - 1)$, measuring attribute sharing across methods. |
| **CBO** | Static | Coupling Between Objects: count of distinct external classes referenced (field types, parameters, return types, throws, class instantiation, inheritance). |
| **NPA** | Static | Number of Public Attributes: fields declared with the `public` modifier. |
| **NPM** | Static | Number of Public Methods: methods declared with the `public` modifier. |
| **NLE** | Static | Nesting Level of Expressions: maximum nesting depth of control flow blocks (`if`, `for`, `while`, `try`, `switch`). |
| **CBOI** | Static | Coupling Between Objects Inward (Afferent Coupling): count of other classes in the repository that depend on or reference this class. |
| **CD** | Static | Comment Density: ratio of comment lines (`//`, `/* ... */`) to total lines ($\text{CLOC} / \max(\text{LOC}, 1)$). |
| **code_churn** | Evolution | Total lines added + total lines deleted for the file across all Git commits in the analyzed history. |
| **revision_count**| Evolution | Total number of commits/revisions that modified the source file. |
| **developer_count**| Evolution | Total number of unique authors/developers who committed modifications to the file. |

---

## 3. Dataset ↔ Git Repository Mapping

- **Dataset**: `Software Metrics for Software Defects Prediction` (JUnit 4 benchmark).
- **Files**: 12 release versions in `data/raw/dataset/junit4/` named `dataset-<commit_hash>.csv`.
- **Commit Mapping**: Each 40-character commit hash (`0550afa689...`, `1b683f4ec0...`, `64155f8a9b...`, etc.) was verified against `https://github.com/junit-team/junit4.git`. Every hash corresponds to an official release tag (e.g. `r4.12`, `r4.13.1`, `r4.9`).
- **File Path Mapping**: 12,244 of 12,245 source rows map to files at their corresponding release commits. The one excluded row, ID `L119`, is non-defective and recorded with its path/reason in `data/derived/junit4_regenerated/unmapped_records.json`. All 264 positive labels are retained.
- **Lookahead Prevention**: For each version dataset, Git evolution metrics are mined *up to that specific commit hash*, ensuring no future changes contaminate past predictions.
- **Original labels**: Every retained row's `isDefective` value matches the raw dataset row by `ID`; labels are copied after feature extraction and excluded from the feature matrix.

---

## 4. Fresh Experimental Evaluation Results

Results evaluated on chronological held-out releases (2,572 samples, 25 defective; 0.97% positive). `PR-AUC` below means average precision; trapezoidal PR area is stored separately in `data/results/evaluation_metrics.json`.

| Model | Features | Accuracy | Precision | Recall | F1 | Balanced accuracy | ROC-AUC | PR-AUC (AP) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | Static | 0.6967 | 0.0166 | 0.5200 | 0.0323 | 0.6092 | 0.6892 | 0.0203 |
| Logistic Regression | Combined | 0.7784 | 0.0244 | 0.5600 | 0.0468 | 0.6703 | 0.7890 | 0.0276 |
| Decision Tree | Static | 0.9184 | 0.0000 | 0.0000 | 0.0000 | 0.4637 | 0.4637 | 0.0097 |
| Decision Tree | Combined | 0.9825 | 0.0455 | 0.0400 | 0.0426 | 0.5159 | 0.5159 | 0.0114 |
| Random Forest | Static | 0.9257 | 0.0000 | 0.0000 | 0.0000 | 0.4674 | 0.5531 | 0.0104 |
| Random Forest | Combined | 0.9759 | 0.0000 | 0.0000 | 0.0000 | 0.4927 | 0.6535 | 0.0160 |

The majority-class baseline has 0.9903 accuracy, 0.5000 balanced accuracy, 0.0000 recall/F1, and 0.0097 average precision. It outperforms all model variants in accuracy. The test set contains only 25 positive labels; all come from r4.12, while r4.13.1 contains zero positives. Do not interpret r4.13.1 accuracy or ranking metrics as defect-detection evidence.

Random Forest predicts positive labels at its default decision rule (166 static, 37 combined) but all are false positives; the maximum score among true defects is below 0.5. No threshold was tuned on the test set.

---

## 5. Final Deployed Model and Explainability

All six classifier/feature-set configurations were evaluated; Logistic Regression Combined was selected based on its leading Average Precision and ROC-AUC. The deployed model is `src/models/saved/LogisticRegression_combined.pkl`, used by the API for individual prediction and repository scanning.

`python src/models/explain.py` generates the Logistic Regression Combined signed/absolute coefficient CSV and positive-class SHAP outputs in `data/results/`. SHAP uses `shap.LinearExplainer` and reports contributions in decision-function (log-odds) space. Its background and explained sample are standardized, ordered 15-feature rows, matching the exact representation consumed by training, evaluation, and deployed inference; generated metadata records the model hash, class, feature order, seed, and additivity/probability validation results. Coefficient signs and magnitudes describe the fitted model per standardized feature unit and are not causal contributions.

The generic legacy `feature_importance.csv`, `shap_values.npy`, `shap_base_values.npy`, and `shap_X_sample.csv` are retained as Random Forest Combined experimental artifacts. They are not consumed as explanations of Logistic Regression. The dashboard and `/feature-importance` endpoint use the explicitly named Logistic Regression Combined artifacts.

**Inference preprocessing:** The API accepts the raw ordered 15-feature schema, applies the saved training medians to any missing values, then applies the persisted training `StandardScaler` before calling the selected model. Both individual prediction and repository scanning use this same path. SHAP is computed over the standardized sample/background data consumed by the classifier. The UI presents the positive-class model output as an uncalibrated 0–1 score; its `HIGH`/`LOW` category is only the configured 0.5 threshold, not a defect confirmation.

Run `python src/models/prediction_audit.py` to reproduce the held-out results, produce descriptive calibration bins/reliability output, measure ranking at selected K values, and inspect feature-range shifts and coefficient contributions on the saved Java Design Patterns feature snapshot. The audit does not fit a calibrator. Its external-repository snapshot has no independently verified defect labels, so it cannot validate live-repository accuracy.

---

## 6. Remaining Limitations

1. **Imbalanced temporal test data**: Only 25/2,572 test rows are positive; the 2020 release has none. Model accuracy is lower than the majority baseline.
2. **Anonymous class records**: 1,837 retained records use synthetic `$n` names and cannot receive a stable source-level FQCN. Their relationship metrics use only relationships that resolve to named source declarations.
3. **Unresolved/external symbols**: Across the 12 repository contexts, 13,116 type references are unresolved/ambiguous within project source and 4,696 are classified as external/standard. No external classpath is available; these references are logged and excluded from project edges, which can undercount coupling/inheritance.
4. **File/class granularity**: Repository scanning returns one row per Java file and selects a primary class, whereas benchmark records can refer to nested classes.
5. **Java parser boundary**: `javalang 0.13.0` rejects records, text blocks, modules, sealed classes, pattern `instanceof`, and switch expressions; unsupported files may use the approximate regex fallback.
6. **History depth and author identity**: Shallow clones limit evolution history; Git author aliases are not canonicalized to human identities.
7. **Class imbalance and external repositories**: The temporal held-out test set is highly imbalanced and may not represent repositories scanned in deployment. Calibrated probability and generalization claims require additional representative evaluation.

**Readiness:** corrected identity metrics and reproducible outputs support controlled follow-up experiments, but the current temporal test set does not support strong predictive-generalization claims.
