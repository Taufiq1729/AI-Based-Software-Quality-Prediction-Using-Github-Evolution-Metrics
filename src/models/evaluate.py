import os
import pandas as pd
import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, roc_curve, precision_recall_curve
import joblib

def get_feature_sets(columns):
    evolution_features = ['code_churn', 'revision_count', 'developer_count']
    static_features = [c for c in columns if c not in evolution_features]
    return static_features, list(columns)

def evaluate_models():
    processed_dir = "data/processed"
    models_dir = "src/models/saved"
    results_dir = "data/results"
    os.makedirs(results_dir, exist_ok=True)
    
    print("Loading test data...")
    X_test = pd.read_csv(os.path.join(processed_dir, "X_test.csv"))
    y_test = pd.read_csv(os.path.join(processed_dir, "y_test.csv")).values.ravel()
    
    static_features, all_features = get_feature_sets(X_test.columns)
    X_test_static = X_test[static_features]
    
    models = ['LogisticRegression', 'DecisionTree', 'RandomForest']
    results = {}
    
    for name in models:
        results[name] = {}
        for feature_set, X in [("static", X_test_static), ("combined", X_test)]:
            model_path = os.path.join(models_dir, f"{name}_{feature_set}.pkl")
            if not os.path.exists(model_path):
                print(f"Model not found: {model_path}")
                continue
                
            model = joblib.load(model_path)
            y_pred = model.predict(X)
            y_prob = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else y_pred
            
            cm = confusion_matrix(y_test, y_pred)
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            prec, rec, _ = precision_recall_curve(y_test, y_prob)
            
            results[name][feature_set] = {
                "Accuracy": float(accuracy_score(y_test, y_pred)),
                "Precision": float(precision_score(y_test, y_pred, zero_division=0)),
                "Recall": float(recall_score(y_test, y_pred, zero_division=0)),
                "F1_Score": float(f1_score(y_test, y_pred, zero_division=0)),
                "ROC_AUC": float(roc_auc_score(y_test, y_prob)),
                "ConfusionMatrix": cm.tolist(),
                "ROC_Curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
                "PR_Curve": {"precision": prec.tolist(), "recall": rec.tolist()}
            }
            
    with open(os.path.join(results_dir, "evaluation_metrics.json"), "w") as f:
        json.dump(results, f, indent=4)
        
    print("Evaluation complete. Results saved to data/results/evaluation_metrics.json")

if __name__ == "__main__":
    evaluate_models()
