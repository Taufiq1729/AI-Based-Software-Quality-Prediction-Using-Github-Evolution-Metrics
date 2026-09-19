from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import json
import os

app = FastAPI(title="SQAM Analytics Engine API")

# Enable CORS for React frontend (defaulting to localhost:5173 for Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ComponentMetrics(BaseModel):
    # Static Metrics
    WMC: float
    DIT: float
    NOC: float
    CBO: float
    RFC: float
    LCOM5: float
    NPA: float
    NPM: float
    NLE: float
    CBOI: float
    CD: float
    LOC: float
    # Evolution Metrics
    code_churn: float
    revision_count: float
    developer_count: float

@app.get("/")
def read_root():
    return {"message": "Welcome to SQAM Analytics Engine API"}

@app.get("/evaluation")
def get_evaluation_metrics():
    results_dir = "data/results"
    metrics_path = os.path.join(results_dir, "evaluation_metrics.json")
    
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Evaluation metrics not found.")
        
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        
    return metrics

@app.get("/feature-importance")
def get_feature_importance():
    results_dir = "data/results"
    importance_path = os.path.join(results_dir, "feature_importance.csv")
    
    if not os.path.exists(importance_path):
        raise HTTPException(status_code=404, detail="Feature importance not found.")
        
    df = pd.read_csv(importance_path)
    return df.to_dict(orient="records")

@app.post("/predict")
def predict_defect_risk(metrics: ComponentMetrics):
    model_path = "src/models/saved/RandomForest_combined.pkl"
    scaler_path = "data/processed/scaler.pkl"
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise HTTPException(status_code=500, detail="Model or Scaler not found. Train models first.")
        
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        
        # Load X_train to get correct column order for scaler
        X_train = pd.read_csv("data/processed/X_train.csv")
        cols = X_train.columns
        
        # Create input dataframe
        input_data = metrics.dict()
        input_df = pd.DataFrame([input_data])[cols]
        
        # Scale
        input_scaled = scaler.transform(input_df)
        
        # Predict
        prob = model.predict_proba(input_scaled)[0][1]
        pred = int(prob > 0.5)
        
        return {
            "prediction": pred,
            "probability": prob,
            "risk_level": "HIGH" if pred == 1 else "LOW"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RepoUrl(BaseModel):
    url: str

@app.post("/scan-repo")
def scan_repository(repo: RepoUrl):
    import tempfile
    import shutil
    import git
    from pydriller import Repository
    import lizard
    
    model_path = "src/models/saved/RandomForest_combined.pkl"
    scaler_path = "data/processed/scaler.pkl"
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise HTTPException(status_code=500, detail="Model or Scaler not found.")
        
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    X_train = pd.read_csv("data/processed/X_train.csv")
    cols = X_train.columns
    
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Clone repository
        git.Repo.clone_from(repo.url, temp_dir)
        
        # 2. Extract static metrics using lizard
        analysis = lizard.analyze([temp_dir])
        file_metrics = {}
        for file_info in analysis:
            if not file_info.filename.endswith('.java'):
                continue
            rel_path = os.path.relpath(file_info.filename, temp_dir)
            file_metrics[rel_path] = {
                'LOC': file_info.nloc,
                'WMC': file_info.average_cyclomatic_complexity * len(file_info.function_list), # Rough WMC proxy
                # Mock complex OO metrics with dataset averages for fast scanning
                'DIT': 2, 'NOC': 0, 'CBO': 12, 'RFC': 25, 
                'LCOM5': 0.4, 'NPA': 0, 'NPM': 5, 'NLE': 1, 
                'CBOI': 3, 'CD': 0.2,
                'code_churn': 0, 'revision_count': 0, 'developer_count': set()
            }
            
        # 3. Extract evolution metrics using PyDriller
        for commit in Repository(temp_dir).traverse_commits():
            for mod in commit.modified_files:
                if mod.new_path and mod.new_path in file_metrics:
                    path = mod.new_path
                    file_metrics[path]['code_churn'] += (mod.added_lines + mod.deleted_lines)
                    file_metrics[path]['revision_count'] += 1
                    file_metrics[path]['developer_count'].add(commit.author.email)
                    
        # 4. Predict risk
        results = []
        for path, metrics in file_metrics.items():
            metrics['developer_count'] = len(metrics['developer_count'])
            if metrics['revision_count'] == 0:
                metrics['developer_count'] = 0
                
            input_df = pd.DataFrame([metrics])[cols]
            input_scaled = scaler.transform(input_df)
            prob = model.predict_proba(input_scaled)[0][1]
            
            results.append({
                "file": path,
                "loc": metrics['LOC'],
                "churn": metrics['code_churn'],
                "revisions": metrics['revision_count'],
                "risk_probability": prob,
                "risk_level": "HIGH" if prob > 0.5 else "LOW"
            })
            
        # Sort by highest risk
        results.sort(key=lambda x: x['risk_probability'], reverse=True)
        return {"files": results[:50]} # Return top 50 high-risk files
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
