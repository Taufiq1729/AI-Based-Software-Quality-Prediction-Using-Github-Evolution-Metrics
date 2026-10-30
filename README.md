# AI-Based Software Quality Prediction Using GitHub Evolution Metrics

**SQAM Analytics Engine** is an AI-powered software quality analysis platform that predicts software defect risk by combining **static source-code metrics** with **Git/GitHub evolution metrics**.

The project provides a machine-learning pipeline, explainability support, a FastAPI backend, and a React/Vite frontend for interactive software-quality analysis.

> **Project:** AI-Based Software Quality Prediction Using GitHub Evolution Metrics  
> **Team:** Taufiq Ansari (23293916007) and Vikash Kumar (23293916049)

---

## Overview

Software quality can be affected by both the internal complexity of source code and the way a software component evolves over time. This project combines these two perspectives to estimate the defect risk of software components.

The system uses:

- **Static code metrics** to represent source-code complexity and structure.
- **Evolution metrics** extracted from Git history to represent how frequently and actively code changes.
- **Machine-learning models** to classify components as lower- or higher-risk.
- **Feature importance and SHAP** for model explainability.
- **FastAPI** to expose prediction and repository-scanning APIs.
- **React + Vite** for the interactive frontend.

The repository currently includes the complete project structure for data acquisition, preprocessing, model training, evaluation, explainability, API services, and frontend integration.

---

## Key Features

### 1. Static Code Analysis

The project works with the following static software metrics:

| Metric | Description |
|---|---|
| WMC | Weighted Methods per Class |
| DIT | Depth of Inheritance Tree |
| NOC | Number of Children |
| CBO | Coupling Between Objects |
| RFC | Response for a Class |
| LCOM5 | Lack of Cohesion of Methods |
| NPA | Number of Public Attributes |
| NPM | Number of Public Methods |
| NLE | Maximum nesting depth of control-flow structures |
| CBOI | Number of other repository classes referencing this class |
| CD | Comment lines divided by lines in the analyzed class span |
| LOC | Lines of Code |

### 2. Git Evolution Analysis

Git history is mined with native Git history commands, following file renames and limiting historical datasets to their matching release commit, to calculate:

- **Code Churn** — added lines + deleted lines.
- **Revision Count** — number of commits affecting a file.
- **Developer Count** — number of unique developers who modified a file.

### 3. Machine Learning

Three classifiers are implemented:

- Logistic Regression
- Decision Tree
- Random Forest

Models are trained using two feature configurations:

1. **Static-only features**
2. **Static + evolution features**

Random Forest uses GridSearchCV over `n_estimators`, `max_depth`, and `min_samples_split`, scored by ROC-AUC with expanding-window folds that hold out complete training releases.

### 4. Model Evaluation

The evaluation pipeline calculates:

- Accuracy
- Precision
- Recall
- F1-score
- Balanced accuracy
- ROC-AUC
- PR-AUC
- Confusion Matrix
- ROC Curve
- Precision-Recall Curve

### 5. Explainable AI

The project supports:

- Random Forest feature importance
- SHAP-based explanations

SHAP explanations are generated using a sample of the test data.

### 6. Repository Scanning

The FastAPI backend provides a `/scan-repo` endpoint that can clone a Git repository, analyze Java files, mine Git history, and return file-level risk predictions.

The response includes information such as:

- File path
- Lines of code
- Code churn
- Revision count
- Risk probability
- Risk level

### 7. Interactive Prediction API

The `/predict` endpoint accepts the project's static and evolution metrics and returns a defect-risk prediction and probability.

---

## Project Architecture

```text
AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics/
│
├── api/
│   └── main.py                     # FastAPI application
│
├── app/                            # Application/dashboard components
│
├── data/
│   ├── raw/                        # Downloaded/raw dataset
│   ├── processed/                  # Processed train/test data and scaler
│   └── results/                    # Evaluation and explainability results
│
├── frontend/                       # React + Vite frontend
│   ├── src/
│   ├── package.json
│   └── ...
│
├── src/
│   ├── data/
│   │   ├── data_acquisition.py     # Dataset download
│   │   ├── preprocessing.py        # Data preprocessing
│   │   └── git_miner.py            # Git evolution metrics
│   │
│   └── models/
│       ├── train.py                # Model training
│       ├── evaluate.py             # Model evaluation
│       ├── explain.py              # Explainability
│       └── saved/                  # Trained models
│
├── requirements.txt
└── README.md
```

---

## Technology Stack

### Backend / Machine Learning

- Python
- Pandas
- NumPy
- Scikit-learn
- Lizard
- SHAP
- Joblib
- FastAPI
- Uvicorn
- GitPython

### Frontend

- React
- Vite
- React Router
- Axios
- Recharts
- Lucide React

---

## Dataset

The project uses the JUnit 4 releases from the **Software Metrics for Software Defects Prediction** dataset. Static features are regenerated from each release's exact Git commit with the same Java analyzer used by repository scanning. Evolution features are mined only through that release commit. One source row has a path that does not exist in its corresponding commit; it is recorded in `data/derived/junit4_regenerated/unmapped_records.json` and excluded, while all retained labels are preserved.

The target variable used by the training pipeline is:

```text
isDefective
```

The chronological holdout uses JUnit 4.8, 4.9, and 4.11 for training (2,251 rows) and JUnit 4.12 and 4.13.1 for testing (2,572 rows). Imputation medians and `StandardScaler` are fitted only on training releases. Model tuning uses earlier training releases to predict later complete releases; held-out test releases are not used in training or tuning.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Taufiq1729/AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics.git
cd AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics
```

### 2. Create a Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Data and Model Pipeline

Run the following commands from the **repository root**.

### Step 1 — Download the Dataset

```bash
python src/data/data_acquisition.py
```

This downloads and extracts the dataset into `data/raw/`.

### Step 2 — Regenerate Release Features

```bash
python src/data/rebuild_static_metrics.py
```

This checks out each dataset commit, builds whole-repository Java context, and writes regenerated static and rename-aware evolution metrics to `data/derived/junit4_regenerated/`.

### Step 3 — Preprocess the Data

```bash
python src/data/preprocessing.py
```

This creates processed training/testing files in:

```text
data/processed/
├── X_train.csv
├── X_test.csv
├── y_train.csv
├── y_test.csv
└── scaler.pkl
```

### Step 4 — Train the Models

```bash
python src/models/train.py
```

The trained models are stored in:

```text
src/models/saved/
```

The pipeline creates static-only and combined versions of the supported classifiers.

### Step 5 — Evaluate the Models

```bash
python src/models/evaluate.py
```

Evaluation results are written to:

```text
data/results/evaluation_metrics.json
```

### Step 6 — Generate Explainability Results

```bash
python src/models/explain.py
```

This generates feature-importance and SHAP-related outputs in `data/results/`.

---

## Running the FastAPI Backend

After preprocessing and model training, start the API with:

```bash
uvicorn api.main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available through FastAPI's generated documentation pages.

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API welcome message |
| GET | `/evaluation` | Retrieve evaluation metrics |
| GET | `/feature-importance` | Retrieve feature-importance data |
| POST | `/predict` | Predict defect risk from supplied metrics |
| POST | `/scan-repo` | Scan a Git repository and predict file-level risk |

---

## `/predict` Example

Send all required static and evolution metrics as JSON:

```json
{
  "WMC": 10,
  "DIT": 2,
  "NOC": 1,
  "CBO": 8,
  "RFC": 20,
  "LCOM5": 0.4,
  "NPA": 1,
  "NPM": 5,
  "NLE": 1,
  "CBOI": 2,
  "CD": 0.2,
  "LOC": 150,
  "code_churn": 80,
  "revision_count": 10,
  "developer_count": 3
}
```

The API returns a result containing:

```json
{
  "prediction": 0,
  "probability": 0.32,
  "risk_level": "LOW"
}
```

The current API uses a probability threshold of `0.5` to classify the result as `HIGH` or `LOW` risk.

---

## Repository Scanning

The `/scan-repo` endpoint accepts a Git repository URL:

```json
{
  "url": "https://github.com/example/repository.git"
}
```

The backend:

1. Clones the repository.
2. Identifies Java source files.
3. Builds whole-repository class context and extracts the shared 12 static metrics.
4. Mines rename-aware Git history for the three evolution metrics.
5. Applies training medians, the saved scaler, and the Random Forest model.
6. Returns the highest-risk files.

The endpoint returns up to **50 files**, sorted by predicted risk probability.

---

## Running the Frontend

The frontend is a React application built with Vite.

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will display the local development URL in the terminal, normally:

```text
http://localhost:5173
```

Make sure the FastAPI backend is running at the same time if the frontend is configured to communicate with the local API.

### Production Build

```bash
npm run build
```

To preview the production build:

```bash
npm run preview
```

---

## Reproducibility Notes

`src/data/feature_extractor.py` defines the shared 15-feature order and extraction path used by training data generation and `/scan-repo`. The API applies the medians and scaler produced by preprocessing. Tests check exact feature parity for the same historical repository snapshot, release-level train/test separation, rename tracking, and exclusion of future Git commits.

The held-out set contains 25 positive labels among 2,572 rows (0.97%); the 2020 release has no positive labels. Interpret precision, recall, F1, balanced accuracy, ROC-AUC, and PR-AUC alongside this class imbalance. The default API classification threshold remains 0.5.

---

## Research Questions

The project is designed around the following research questions:

### RQ1
Does combining evolution/process metrics such as code churn, revision count, and developer count with static code metrics improve defect-proneness prediction compared with using static metrics alone?

### RQ2
Which static and evolution metrics contribute most to defect-risk prediction?

### RQ3
How do Logistic Regression, Decision Tree, and Random Forest compare when predicting software defect risk using the selected feature sets?

### RQ4
Can feature importance and SHAP explanations identify meaningful and actionable software-quality indicators?

---

## Expected Workflow

```text
                ┌─────────────────────┐
                │   Dataset / GitHub  │
                │     Repository      │
                └──────────┬──────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
    ┌──────────────────┐       ┌──────────────────┐
    │ Static Metrics   │       │ Git Evolution    │
    │ LOC, WMC, CK...  │       │ Churn, Revisions│
    └────────┬─────────┘       │ Developers      │
             │                 └────────┬─────────┘
             └────────────┬────────────┘
                          ▼
                ┌─────────────────────┐
                │ Data Preprocessing  │
                │ Split + Scaling     │
                └──────────┬──────────┘
                           ▼
                ┌─────────────────────┐
                │ Machine Learning    │
                │ LR / DT / RF        │
                └──────────┬──────────┘
                           ▼
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌──────────────────┐       ┌──────────────────┐
    │ Model Evaluation │       │ Explainability   │
    │ Metrics + Curves │       │ Importance + SHAP│
    └────────┬─────────┘       └────────┬─────────┘
             └────────────┬────────────┘
                          ▼
                ┌─────────────────────┐
                │ FastAPI + Frontend  │
                │ Risk Prediction     │
                └─────────────────────┘
```

---

## Output Files

After running the pipeline, the main generated artifacts include:

```text
data/
├── processed/
│   ├── X_train.csv
│   ├── X_test.csv
│   ├── y_train.csv
│   ├── y_test.csv
│   └── scaler.pkl
│
└── results/
    ├── evaluation_metrics.json
    ├── feature_importance.csv
    └── SHAP-related output files

src/models/saved/
├── LogisticRegression_static.pkl
├── LogisticRegression_combined.pkl
├── DecisionTree_static.pkl
├── DecisionTree_combined.pkl
├── RandomForest_static.pkl
└── RandomForest_combined.pkl
```

---

## Applications

The system can be used as a prototype for:

- Identifying potentially defect-prone software components.
- Supporting software quality assurance activities.
- Prioritizing files for code review or testing.
- Studying the relationship between code complexity and software evolution.
- Exploring explainable machine-learning approaches for software-quality prediction.

---

## Future Improvements

Potential extensions include:

- Evaluate additional releases and projects with release-specific holdouts and adequate positive labels.
- Improve class-level mapping for Java files that contain multiple top-level or nested classes.
- Resolve inheritance and coupling against external classpaths where those dependencies are available.
- Calibrate the decision threshold using training-period validation data.
- Expand repository-language support beyond Java.
- Add richer SHAP visualizations and explanation reports.
- Integrate automated CI/CD quality checks.
- Add authentication and deployment configuration for production use.

---

## Authors

**Taufiq Ansari**  
Enrollment No.: 23293916007

**Vikash Kumar**  
Enrollment No.: 23293916049

---

## License

No explicit license is currently specified in the repository. If this project is intended for public reuse, add an appropriate `LICENSE` file to the repository.

---

## Repository

[AI-Based Software Quality Prediction Using GitHub Evolution Metrics](https://github.com/Taufiq1729/AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics)
