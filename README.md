# AI-Based Software Quality Prediction Using GitHub Evolution Metrics

**SQAM Analytics Engine** is a research prototype that estimates the defect risk of Java source files by combining static source-code metrics with Git-based software evolution metrics.

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

---

## Explainability

The project includes:

- Random Forest feature-importance output.
- SHAP values and a corresponding sample of feature rows.

**Artifact/model alignment:** The currently saved feature-importance and SHAP artifacts explain the **Random Forest combined** model. They should not be presented as explanations of the Logistic Regression model. If explanations are required for the Logistic Regression model used by the scanner, generate a new explanation artifact specifically for that model.

---

## Repository Scanning and Prediction

The FastAPI application provides endpoints for metric-based prediction and Java repository scanning.

### Repository scanning

The `/scan-repo` endpoint accepts a Git repository URL, clones the repository, identifies Java source files, extracts the shared feature set, and returns file-level defect-risk scores.

The scanning workflow is intended to:

1. Clone the supplied Git repository.
2. Identify `.java` source files.
3. Build repository context and extract the 12 static metrics.
4. Mine Git history for `code_churn`, `revision_count`, and `developer_count`.
5. Arrange the extracted values in the exact 15-feature schema.
6. Apply the currently configured combined Logistic Regression model.
7. Return file-level risk probabilities and risk labels, with higher-risk files prioritized in the response.

The current scanner is Java-only because the feature extractor and training data are Java-specific. Risk scores are estimates from the trained model and should be used to help prioritize manual review, not interpreted as confirmed defects.

### Prediction endpoint

The `/predict` endpoint accepts the model's required static and evolution metrics and returns a prediction and probability. The current API uses a probability threshold of `0.5` to map the score to its `HIGH` or `LOW` risk label. This is the configured application threshold; it is not a threshold optimized on the held-out test set.

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
  "risk_level": "LOW"
}
```

The values above are illustrative request/response examples, not measured results.

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

The exact files generated depend on the preprocessing script. The current `train.py` and `evaluate.py` workflows consume these feature and label CSVs. They pass the resulting feature matrices directly to the models; do not add an external scaler or imputer at evaluation time unless the training and evaluation implementation is deliberately changed to use one consistently.

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
