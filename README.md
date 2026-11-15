# AI-Based Software Quality Prediction Using GitHub Evolution Metrics

> **Project:** AI-Based Software Quality Prediction Using GitHub Evolution Metrics  
> **Team:** Taufiq Ansari and Vikash Kumar  
> **Repository:** [GitHub](https://github.com/Taufiq1729/AI-Based-Software-Quality-Prediction-Using-Github-Evolution-Metrics)

---

## 📌 Project Overview

**CodeQuality AI (SQAM Analytics Engine)** is a research prototype that analyzes Java repositories with static source-code metrics and Git-based software evolution metrics, then ranks file-level model estimates to help prioritize manual code reviews and automated testing.

Software defect risk is associated with both the static structure of source code and the way that code evolves over time. Traditional software quality assurance (SQA) relies heavily on static code metrics (such as the Chidamber & Kemerer metric suite: WMC, DIT, NOC, CBO, RFC, and LCOM). While static metrics capture structural complexity and coupling, they present only a static snapshot of source code. A structurally complex class that rarely changes may stay defect-free, while an apparently simple class undergoing rapid, churn-heavy revisions across multiple authors often becomes a hotspot for regressions.

The platform unites:
1. **12 Static OO Metrics** (source-code structure, complexity, cohesion, inheritance, and coupling).
2. **3 Git Evolution Metrics** (historical code churn, revision frequency, and distinct developer count).

By fusing source-code AST parsing with repository commit history, the platform trains and executes 6 Machine Learning configurations to identify defect-prone Java files and generate SHAP explainability insights.

---

## 🚀 Main Capabilities

- **Real Java AST Analysis**: Extracts 12 static metrics using `javalang` and `lizard`.
- **Real Git History Mining**: Mines code churn (lines added + deleted), revision frequency, and distinct developers across Git commit history, preserving file renames.
- **6 Machine-Learning Configurations**:
  - `Logistic Regression (Combined)` – **Primary Champion Model**
  - `Logistic Regression (Static Only)`
  - `Random Forest (Combined)`
  - `Random Forest (Static Only)`
  - `Decision Tree (Combined)`
  - `Decision Tree (Static Only)`
- **Interactive Web Dashboard**:
  - KPI summary cards (Total Java files, High/Low risk counts, Average defect risk, Commits, Contributors).
  - Dynamic classification threshold slider (0.10 to 0.90, default 0.50) with real-time updates.
  - Interactive Recharts visualizations: risk distribution pie chart, severity histogram, top 10 hotspot files.
- **Searchable File Explorer**:
  - Sortable and filterable table by LOC, churn, revisions, developers, and risk score.
  - Deep-dive diagnostic modal with all 15 metrics, radar chart, and SHAP waterfall.
  - One-click downloadable CSV report.
- **SHAP Diagnostics & Natural Language Explanations**:
  - File-level feature contribution breakdown.
  - Human-readable narrative explaining why each file received its score.
  - Radar chart comparing the file's metrics against repository-wide averages.
- **Research Evaluation & Benchmark Comparison**:
  - Dedicated section presenting official paper benchmark results showing empirical gains from adding Git evolution metrics (+36.0% Average Precision).
  - ROC and Precision-Recall curves, confusion matrices, and model comparison.
- **Component Simulator**:
  - Interactive sliders to test hypothetical Java class designs before committing code.

---

## 📊 Software Metrics Specification (15 Features)

### 12 Static Object-Oriented Metrics
| Metric | Full Name | Description & Impact |
|:---|:---|:---|
| **LOC** | Lines of Code | Non-comment, non-blank source lines of code (`nloc`). |
| **WMC** | Weighted Methods per Class | Sum of cyclomatic complexity across class methods. |
| **DIT** | Depth of Inheritance Tree | Longest path from class to root `Object` in inheritance tree. |
| **NOC** | Number of Children | Direct subclasses extending this class in the repository. |
| **CBO** | Coupling Between Object Classes | Count of distinct non-primitive classes referenced via fields, calls, parameters, and returns. |
| **RFC** | Response for a Class | Number of local methods declared + distinct external methods invoked. |
| **LCOM5** | Lack of Cohesion of Methods | Henderson-Sellers cohesion metric evaluating method-field access overlap. |
| **NPA** | Number of Public Attributes | Count of public fields declared in the class. |
| **NPM** | Number of Public Methods | Count of public methods exposed in the class interface. |
| **NLE** | Nesting Level Else-If | Maximum nesting depth of compound control statements (`if`, `for`, `while`, `switch`). |
| **CBOI** | Inverse Coupling (Afferent) | Count of other repository classes that depend upon this class. |
| **CD** | Comment Density | Ratio of comment lines to total lines (`comments / [LOC + comments]`). |

### 3 Git Evolution Metrics
| Metric | Formula | Description & Impact |
|:---|:---|:---|
| **Code Churn** | $\text{Lines Added} + \text{Lines Deleted}$ | Measures volatility and churn across the commit history. |
| **Revision Count** | $\sum \text{Commits modifying file}$ | Identifies modification hotspots across the repository lifecycle. |
| **Developer Count** | $\vert \text{Distinct Authors} \vert$ | Measures code ownership diffusion across contributors. |

---

## 📈 Empirical Research Benchmark Results

| Model Configuration | Avg Precision (AP) | ROC-AUC | Precision | Recall | F1-Score | Accuracy |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Logistic Regression (Combined) ★** | **0.0276** | **0.7890** | **0.0244** | **0.5600** | **0.0468** | **0.7784** |
| Logistic Regression (Static Only) | 0.0203 | 0.6892 | 0.0185 | 0.4500 | 0.0355 | 0.7410 |
| **Random Forest (Combined)** | **0.0160** | **0.7320** | **0.0180** | **0.4400** | **0.0345** | **0.8920** |
| Random Forest (Static Only) | 0.0104 | 0.6810 | 0.0125 | 0.3500 | 0.0241 | 0.8850 |
| **Decision Tree (Combined)** | **0.0114** | **0.6450** | **0.0135** | **0.3800** | **0.0260** | **0.8240** |
| Decision Tree (Static Only) | 0.0097 | 0.5980 | 0.0110 | 0.3200 | 0.0212 | 0.8120 |

> **Key Finding**: Adding Git evolution metrics yielded a **+36.0% relative improvement in Average Precision** for Logistic Regression and a **+53.8% boost** for Random Forest.

---

## 🏗️ Architecture & Project Structure

```
.
├── api/                             # FastAPI Backend Engine
│   ├── github_service.py            # URL validation, cloning, commit metadata
│   ├── java_analyzer.py             # Java file discovery and project-wide coupling resolution
│   ├── static_metrics.py            # AST parsing (javalang + lizard) for 12 static metrics
│   ├── git_metrics.py               # Fast Git log mining (churn, revisions, developers)
│   ├── feature_processor.py         # 15-feature ordering, imputation, and StandardScaler
│   ├── prediction_service.py        # ML inference across 6 configurations and thresholding
│   ├── explainability.py            # SHAP LinearExplainer/TreeExplainer & natural narrative generator
│   ├── evaluation_service.py        # Research paper benchmarks & test split metrics
│   └── main.py                      # REST API endpoints, CORS, background scan workers
│
├── frontend/                        # React + Vite + Tailwind CSS Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navigation.jsx       # Sidebar (desktop) & Header (mobile) with dark/light mode
│   │   │   ├── MetricTooltip.jsx    # Metric explanations and engineering impact
│   │   │   └── FileDetailModal.jsx  # Deep-dive file inspection, radar chart & SHAP waterfall
│   │   ├── context/
│   │   │   └── ScanContext.jsx      # Centralized state for scans, models, thresholds, and theme
│   │   ├── pages/
│   │   │   ├── Home.jsx             # Hero, URL input, quick-select sample repos, config
│   │   │   ├── LiveAnalysis.jsx     # Real-time multi-stage pipeline status & stdout logs
│   │   │   ├── Dashboard.jsx        # KPI summary, threshold slider, Recharts visualizations
│   │   │   ├── FileExplorer.jsx     # Searchable, sortable, paginated table & CSV export
│   │   │   ├── ModelEvaluation.jsx  # Benchmark matrices, ROC/PR curves, feature importance
│   │   │   ├── Simulator.jsx        # Interactive 15-metric component simulator with presets
│   │   │   └── About.jsx            # Research methodology & complete metric dictionary
│   │   ├── App.jsx                  # Route definitions
│   │   └── index.css                # Tailwind directives & responsive styles
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── audit/                       # Release distribution, static parity & model reproducibility audits
│   ├── processed/                   # scaler.pkl and chronologically split train/test datasets
│   └── results/                     # evaluation_metrics.json, feature_importance.csv, prediction_audit.json
│
├── src/
│   ├── analyzers/                   # Java AST and project reference analyzer
│   ├── data/                        # Feature extractors, preprocessing, and miner pipelines
│   └── models/                      # Training, evaluation, explanation, and saved models (.pkl)
│       └── saved/                   # 6 pre-trained model PKLs
│
├── tests/                           # Unit and integration test suites
│   ├── test_api.py
│   ├── test_benchmark_static_parity.py
│   ├── test_pipeline.py
│   └── test_prediction_audit.py
│
├── requirements.txt                 # Python dependencies
└── README.md
```

---

## ⚙️ Installation & Local Execution

### Prerequisites
- **Python 3.10+** (or virtual environment)
- **Node.js 18+** & npm
- **Git** installed and available in PATH

### 1. Backend Setup (FastAPI)

```bash
# From the project root
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server on port 8000
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API and interactive documentation will be available at:
- **API Base**: `http://127.0.0.1:8000`
- **Swagger Docs**: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup (React + Vite)

In a new terminal window:
```bash
# Navigate to the frontend directory
cd frontend

# Install frontend dependencies
npm install

# Start the Vite development server
npm run dev
```
The web dashboard will be available at:
- **Web App**: `http://localhost:5173`

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/` | API status and root information |
| `GET` | `/evaluation` | Evaluation metrics from dataset validation |
| `GET` | `/prediction-audit` | Model calibration bins and repository distribution diagnostics |
| `GET` | `/feature-importance` | Global feature importance rankings |
| `POST` | `/predict` | Predicts defect risk for a raw 15-feature component vector |
| `POST` | `/scan-repo` | Clones repository, extracts metrics, and returns scored files |
| `GET` | `/api/sample-repos` | Returns curated public Java repositories for quick testing |
| `POST` | `/api/validate-repo` | Validates GitHub URL syntax and remote accessibility |
| `POST` | `/api/scan-repo` | Initiates background cloning, AST parsing, Git mining, and scoring |
| `GET` | `/api/scan-status/{task_id}` | Polls real-time progress (0.0 to 1.0) and live logs |
| `GET` | `/api/scan-results/{task_id}` | Retrieves full file analysis; supports dynamic `?model=` and `?threshold=` |
| `GET` | `/api/file-detail/{task_id}` | Detailed file metrics, repository comparison radar, and SHAP drivers |
| `POST` | `/api/predict-component` | Predicts defect risk and SHAP explanation for a single component |
| `GET` | `/api/model-evaluation` | Returns official paper benchmarks and local pipeline evaluation metrics |
| `GET` | `/api/export-csv/{task_id}` | Streams complete analysis results as a downloadable CSV report |

---

## ⚖️ Research Constraints & Disclaimers

1. **Java Language Specialization**: CodeQuality AI currently parses and analyzes Java (`.java`) repositories. Other languages are not supported.
2. **Relative Risk Indicator**: The predicted score represents a relative defect-risk indicator derived from structural complexity and historical change volatility. It does not certify that a class definitely contains bugs.
3. **Threshold Calibration**: The default classification threshold is `0.50`. Users may adjust the sensitivity slider to suit aggressive or conservative quality assurance workflows.
4. **Constructive Utilization**: Defect risk scores are intended to guide code peer reviews, unit test coverage, and refactoring planning—never as punitive metrics for engineering performance.

---

## 👥 Authors

- **Taufiq Ansari**
- **Vikash Kumar**
