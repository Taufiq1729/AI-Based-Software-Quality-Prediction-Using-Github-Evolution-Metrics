# AI-Based Software Quality Prediction Using GitHub Evolution Metrics

**SQAM Analytics Engine** is a research prototype that analyzes Java repositories with static source-code metrics and Git-based software evolution metrics, then ranks file-level model estimates to help prioritize manual review. Scores do not confirm defects and are not calibrated defect probabilities.

The project investigates whether information about a file's development history—such as code churn, revision frequency, and contributor count—adds predictive value beyond measurements of the source code itself. It includes a reproducible machine-learning workflow, model evaluation and explainability artifacts, a FastAPI backend, and a React/Vite frontend for repository-level analysis.

> **Project:** AI-Based Software Quality Prediction Using GitHub Evolution Metrics  
> **Team:** Taufiq Ansari and Vikash Kumar

---

## Project Objective

Software defect risk may be associated with both the structure of source code and the way that code changes over time. This project compares models trained on:

1. **Static-only features** — measurements of source-code structure and complexity.
2. **Combined features** — the same static measurements plus Git evolution metrics.

The experimental objective is to assess whether adding evolution metrics improves defect-proneness ranking and prediction on later, chronologically held-out JUnit 4 releases.

**Scope:** The current feature extractor and trained dataset are Java-specific. Repository scanning currently analyzes `.java` files; Python, JavaScript, and other languages are possible future extensions, not supported capabilities of the current trained system.

## Main Capabilities

- Extract 12 static Java source-code metrics.
- Mine 3 evolution metrics from Git history.
- Train and compare Logistic Regression, Decision Tree, and Random Forest classifiers.
- Compare static-only and static-plus-evolution feature configurations.
- Evaluate models on chronologically held-out releases.
- Produce evaluation metrics, ROC and precision-recall curve data, and confusion matrices.
- Provide feature-importance and SHAP explainability artifacts.
- Expose prediction and Java repository-scanning endpoints through FastAPI.
- Present the analysis through a React/Vite frontend.

---

## Feature Set

The model uses a fixed, ordered set of 15 features.

### Static source-code metrics

| Feature | Description |
|---|---|
| `LOC` | Lines of Code |
| `WMC` | Weighted Methods per Class |
| `DIT` | Depth of Inheritance Tree |
| `NOC` | Number of Children |
| `RFC` | Response for a Class |
| `LCOM5` | Lack of Cohesion of Methods (LCOM5) |
| `CBO` | Coupling Between Objects |
| `NPA` | Number of Public Attributes |
| `NPM` | Number of Public Methods |
| `NLE` | Maximum nesting depth of control-flow structures |
| `CBOI` | Number of other repository classes referencing the class |
| `CD` | Comment lines divided by lines in the analyzed class span |

### Git evolution metrics

| Feature | Description |
|---|---|
| `code_churn` | Added lines plus deleted lines |
| `revision_count` | Number of commits affecting the file |
| `developer_count` | Number of distinct developers who modified the file |

The **static-only** configuration uses the 12 static features. The **combined** configuration uses all 15 features. The feature order is defined by the shared feature schema in `src/data/feature_extractor.py`; training, evaluation, prediction, and repository scanning must preserve that order.

---

## Machine-Learning Experiments

Three classifiers are compared:

- Logistic Regression
- Decision Tree
- Random Forest

Each classifier is trained in two configurations: static-only and combined. Random Forest hyperparameters are selected using GridSearchCV with release-aware, expanding-window validation on the training releases.

### Dataset and chronological evaluation

The experiments use JUnit 4 releases from the **Software Metrics for Software Defects Prediction** dataset. Static metrics are regenerated from the corresponding historical Java source snapshots, and Git evolution metrics are mined only up to the matching release commit. This avoids using future repository history when constructing historical features.

One source record could not be mapped to a file in its corresponding historical commit and was excluded; the retained records keep their original defect labels.

| Partition | Releases | Rows |
|---|---|---:|
| Training | JUnit 4.8, 4.9, 4.11 | 2,251 |
| Held-out test | JUnit 4.12, 4.13.1 | 2,572 |

The held-out test set contains **25 defective** and **2,547 non-defective** records. The positive class is therefore highly underrepresented. In addition, the positive examples are concentrated in one of the held-out releases, while the other held-out release contains no positive examples. Metrics must be interpreted with this class imbalance and release composition in mind.

### Reported held-out results

Average Precision (AP) is especially relevant for this imbalanced classification task. The table below reports the final evaluation results for AP and ROC-AUC.

| Classifier | Feature configuration | Average Precision | ROC-AUC |
|---|---|---:|---:|
| Logistic Regression | Static-only | 0.02027 | 0.68918 |
| Logistic Regression | Combined | **0.02758** | **0.78898** |
| Decision Tree | Static-only | 0.00972 | 0.46368 |
| Decision Tree | Combined | 0.01144 | 0.51590 |
| Random Forest | Static-only | 0.01036 | 0.55311 |
| Random Forest | Combined | 0.01600 | 0.65349 |

The majority-class/prevalence baseline has an Average Precision of approximately **0.00972**. Adding evolution features improves AP for all three classifiers in this experiment. Logistic Regression with combined features has the strongest AP and ROC-AUC among the six evaluated configurations.

These results show a relative improvement from adding evolution features, but the absolute AP and precision values remain low. The system should therefore be treated as a **research and triage aid**, not as a definitive defect detector or a replacement for testing, code review, or engineering judgement.

The evaluation pipeline also records accuracy, balanced accuracy, precision, recall, F1-score, confusion matrices, ROC curve coordinates, precision-recall curve coordinates, and per-release results in `data/results/evaluation_metrics.json`.

**Final model:** all six classifier/configuration combinations (three classifiers, each with static-only and combined features) were trained and evaluated. **Logistic Regression Combined** was selected as the final model and is saved as `src/models/saved/LogisticRegression_combined.pkl`. Its reported held-out results are AP 0.02758, ROC-AUC 0.78898, precision 0.02443, recall 0.56, and F1-score 0.04682. The FastAPI individual-prediction and repository-scanning endpoints both load this same model.

---

## Explainability

Feature-importance coefficients and SHAP explanations are generated specifically for **Logistic Regression Combined**, the final model used by both API prediction and repository scanning. Run:

```bash
python src/models/explain.py
```

The model-specific outputs in `data/results/` are:

- `logistic_regression_combined_feature_coefficients.csv` — signed learned coefficients and absolute coefficient magnitudes, in the authoritative 15-feature order. Coefficients describe model behavior, not causal contributions; magnitudes depend on input scale.
- `logistic_regression_combined_shap_values.npy`, `logistic_regression_combined_shap_X_sample.csv`, and `logistic_regression_combined_shap_base_values.npy` — class-1 SHAP values, their standardized model-input rows, and the log-odds base value.
- `logistic_regression_combined_shap_background.csv` and `logistic_regression_combined_explanation_metadata.json` — the reproducible SHAP background rows and model identity, feature order, output space, and validation results.

The previous generic `feature_importance.csv`, `shap_values.npy`, `shap_X_sample.csv`, and `shap_base_values.npy` files are retained as supplementary **Random Forest Combined** experiment outputs. They are not consumed by the Logistic Regression dashboard or `/feature-importance` endpoint and must not be described as explanations of Logistic Regression.

---

## Repository Scanning and Prediction

The FastAPI application provides endpoints for metric-based prediction and Java repository scanning.

### Repository scanning

The `/scan-repo` endpoint accepts a Git repository URL, clones the repository, identifies Java source files, extracts the shared feature set, and returns ranked file-level model scores, commit identity, extraction counts, and diagnostics. Each result is one primary file-level prediction; additional and nested classes are not scored independently.

The scanning workflow is intended to:

1. Clone the supplied Git repository.
2. Identify `.java` source files.
3. Build repository context and extract the 12 static metrics.
4. Mine Git history for `code_churn`, `revision_count`, and `developer_count`.
5. Arrange the extracted values in the exact 15-feature schema, fill missing values with the saved training medians, and apply the saved training `StandardScaler`.
6. Apply the combined Logistic Regression model to the standardized feature rows.
7. Rank successfully scored files by descending class-1 score. Exact score ties are ordered by case-insensitive file path, then exact file path; tied files share a relative-priority tier. Ranking and priority tiers are review aids, not absolute defect-risk categories.
8. Return `rank`, `priority`, `score_tie_count`, the original file path, all 15 metrics, and the total counts for discovered, analyzed, scored and returned files. By default the API keeps its top-50 response limit for compatibility; pass `?limit=10`, `20`, or `50` to choose a result cap, or `?limit=0` to return all successfully scored files. The frontend requests all ranked files so its Top 10/20/50/All, search and sorting controls apply to the complete scan.

The relative-priority rule labels rank 1 (and any files tied with it) **Highest priority**. Remaining score-tie groups are assigned by their midpoint position in the complete ranking: top quartile **High relative priority**, middle half **Medium relative priority**, final quartile **Lower relative priority**. Equal scores do not indicate meaningfully different model estimates.

The legacy `risk_probability` and `risk_level` response fields remain for compatibility; the score is uncalibrated and the label is the model's default binary prediction, not a validated repository risk category.

The current scanner is Java-only because the feature extractor and training data are Java-specific. Scores are estimates from the trained model and should be used to help prioritize manual review, not interpreted as confirmed defects.

### Prediction endpoint

The `/predict` endpoint remains available for internal testing and accepts the model's raw static and evolution metrics, applies the saved training median imputation and `StandardScaler`, and returns a prediction and model score. Repository scanning uses the same preprocessing, model, and positive-class output. Its legacy `risk_level` field reflects the classifier's default 0.5 decision threshold; it is not a risk-severity classification and was not optimized on the held-out test set. The primary frontend navigation focuses on Home, How It Works, Analytics and Repository Scanner. The manual predictor remains reachable directly at `/predictor` for developer experimentation and is not part of the repository-scanning journey.

Example request body:

```json
{
  "LOC": 150,
  "WMC": 10,
  "DIT": 2,
  "NOC": 1,
  "RFC": 20,
  "LCOM5": 0.4,
  "CBO": 8,
  "NPA": 1,
  "NPM": 5,
  "NLE": 1,
  "CBOI": 2,
  "CD": 0.2,
  "code_churn": 80,
  "revision_count": 10,
  "developer_count": 3
}
```

Example response shape:

```json
{
  "prediction": 0,
  "probability": 0.32,
  "model_score": 0.32,
  "risk_level": "LOW",
  "probability_interpretation": "uncalibrated_model_estimate"
}
```

The values above are illustrative request/response examples, not measured results. `probability` is retained for API compatibility; use `model_score` and the interpretation field, and do not read this output as a calibrated probability.

### Prediction-score audit

Run `python src/models/prediction_audit.py` to reproduce held-out metrics, examine score calibration descriptively, calculate held-out top-K ranking results, and inspect feature distributions and model contributions for the saved Java Design Patterns feature snapshot. Outputs are written to `data/results/prediction_audit*`. The snapshot's stored legacy scores were generated by the model named in its metadata; audit scores are recalculated with Logistic Regression Combined and do not represent a new live scan.

The audit does not fit a calibrator or claim that predictions on an external repository are correct: no independently labeled external repository scan is available. See the [prediction-score audit](./docs/FINAL_VALIDATION_AUDIT.md#prediction-score-audit) for the recorded findings and limitations.

---

## Technology Stack

### Backend and machine learning

- Python
- Pandas and NumPy
- scikit-learn
- Lizard / Java source analysis
- SHAP
- Joblib
- FastAPI and Uvicorn
- Git-based history mining

### Frontend

- React
- Vite
- React Router
- Axios
- Recharts
- Lucide React

---

## Project Structure

The following is the intended high-level structure. Exact folders and generated artifacts may vary by branch and local setup.

```text
AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics/
│
├── api/
│   └── main.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── derived/
│   └── results/
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── src/
│   ├── data/
│   │   ├── data_acquisition.py
│   │   ├── preprocessing.py
│   │   ├── feature_extractor.py
│   │   └── git_miner.py
│   │
│   └── models/
│       ├── train.py
│       ├── evaluate.py
│       ├── explain.py
│       └── saved/
│
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Taufiq1729/AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics.git
cd AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics
```

### 2. Create and activate a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Reproducing the Data and Model Pipeline

Run commands from the repository root. Use the scripts and paths present in the checked-out branch; filenames can differ if the project structure has changed.

### Step 1 — Acquire the dataset

```bash
python src/data/data_acquisition.py
```

This downloads and extracts the source dataset into the raw-data directory, subject to the script's configuration and dataset availability.

### Step 2 — Rebuild historical features

```bash
python src/data/rebuild_static_metrics.py
```

This regenerates Java static metrics from historical release snapshots and mines evolution metrics from the corresponding Git history.

### Step 3 — Preprocess and create chronological partitions

```bash
python src/data/preprocessing.py
```

The training and evaluation workflow uses separate feature and label files:

```text
data/processed/
├── X_train.csv
├── X_test.csv
├── y_train.csv
└── y_test.csv
```

The preprocessing script imputes using training medians and standardizes `X_train.csv` and `X_test.csv`; the training and evaluation scripts pass these standardized matrices directly to the classifiers. The API accepts raw ordered feature values, validates them, and applies the saved training scaler before prediction. The explainability generator uses the same standardized model-input representation as training, evaluation, and inference. Do not feed unscaled raw feature values directly to the saved classifier.

### Step 4 — Train models

```bash
python src/models/train.py
```

The six trained model files are stored under `src/models/saved/`:

```text
LogisticRegression_static.pkl
LogisticRegression_combined.pkl
DecisionTree_static.pkl
DecisionTree_combined.pkl
RandomForest_static.pkl
RandomForest_combined.pkl
```

### Step 5 — Evaluate models

```bash
python src/models/evaluate.py
```

The evaluation results are written to:

```text
data/results/evaluation_metrics.json
```

### Step 6 — Generate explainability artifacts

```bash
python src/models/explain.py
```

This generates feature-importance and SHAP-related outputs under `data/results/`. Confirm which model each artifact explains before using it in a report or visualization.

---

## Running the FastAPI Backend

After the required model artifacts are available, start the API from the repository root:

```bash
uvicorn api.main:app --reload
```

The local API is normally available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is normally available at:

```text
http://127.0.0.1:8000/docs
```

### API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API welcome/status |
| `GET` | `/evaluation` | Retrieve evaluation metrics |
| `GET` | `/prediction-audit` | Retrieve prediction calibration and saved-repository feature-range audit summaries |
| `GET` | `/feature-importance` | Retrieve feature-importance data |
| `POST` | `/predict` | Predict risk from supplied metrics |
| `POST` | `/scan-repo` | Scan a Git repository and return Java file-level risk estimates |

Check `api/main.py` in the current branch for the definitive request schema and endpoint behavior.

---

## Running the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite prints the local development URL, normally:

```text
http://localhost:5173
```

The FastAPI backend must also be running if the frontend is configured to call the local API.
The frontend defaults to `http://localhost:8000`; set `VITE_API_BASE_URL` before `npm run dev` or `npm run build` if the API is hosted elsewhere.

### Production build

```bash
npm run build
```

To preview the production build:

```bash
npm run preview
```

---

## Reproducibility and Interpretation Notes

- `src/data/feature_extractor.py` defines the shared 15-feature schema. Preserve its exact feature names and order across extraction, training, evaluation, and scanning.
- Historical feature generation must use the matching release snapshot and must not include commits made after that snapshot.
- The held-out test set is highly imbalanced: 25 positive labels out of 2,572 records.
- One held-out release has no positive examples, so per-release metrics for that release cannot demonstrate positive-class detection.
- Average Precision and precision-recall analysis are important alongside ROC-AUC for this class distribution.
- The configured API risk threshold of `0.5` is not a threshold selected using the held-out test labels.
- The current scanner's Java-only scope reflects the language coverage of the extractor and training data.
- The scanner's risk score is a prioritization signal, not proof that a file contains a defect.

---

## Research Questions

**RQ1.** Does combining Git evolution metrics—code churn, revision count, and developer count—with static source-code metrics improve defect-risk prediction compared with static metrics alone?

**RQ2.** Which static and evolution metrics contribute most to defect-risk prediction?

**RQ3.** How do Logistic Regression, Decision Tree, and Random Forest compare across the static-only and combined feature configurations?

**RQ4.** Can feature-importance and SHAP explanations provide useful insight into the model's predictions?

---

## Future Work

- Extend the training dataset and evaluation to additional Java projects and releases.
- Improve class-level mapping for Java files containing multiple top-level or nested classes.
- Improve resolution of inheritance and coupling relationships involving external classpaths.
- Investigate training-period threshold selection and probability calibration.
- Extend feature extraction and build suitable labelled datasets for Python, JavaScript, and other programming languages.
- Generate model-specific explanations for the classifier deployed by the scanner.
- Improve the robustness of defect prediction under severe class imbalance and release-to-release distribution changes.
- Explore CI/CD integration as a quality-assurance aid.

---

## Authors

**Taufiq Ansari**

**Vikash Kumar**

---

## Repository

[AI-Based Software Quality Prediction Using GitHub Evolution Metrics](https://github.com/Taufiq1729/AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics)
