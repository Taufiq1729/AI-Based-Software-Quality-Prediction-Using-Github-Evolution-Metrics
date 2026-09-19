import os
import pandas as pd
import numpy as np
import shap
import joblib
import json

def generate_explanations():
    processed_dir = "data/processed"
    models_dir = "src/models/saved"
    results_dir = "data/results"
    
    print("Loading test data...")
    X_test = pd.read_csv(os.path.join(processed_dir, "X_test.csv"))
    
    model_path = os.path.join(models_dir, "RandomForest_combined.pkl")
    if not os.path.exists(model_path):
        print("Random Forest combined model not found. Run train.py first.")
        return
        
    model = joblib.load(model_path)
    
    print("Extracting feature importance...")
    importances = model.feature_importances_
    features = X_test.columns
    
    feature_importance = pd.DataFrame({'Feature': features, 'Importance': importances})
    feature_importance = feature_importance.sort_values(by='Importance', ascending=False)
    feature_importance.to_csv(os.path.join(results_dir, "feature_importance.csv"), index=False)
    
    print("Generating SHAP values (this may take a moment)...")
    # Using a background dataset (subset) to speed up SHAP
    explainer = shap.TreeExplainer(model)
    # Just take 100 samples for the web dashboard visualization cache
    X_sample = X_test.sample(n=min(100, len(X_test)), random_state=42)
    shap_values = explainer.shap_values(X_sample)
    
    # Save the base values and SHAP values for class 1 (defective)
    if isinstance(shap_values, list):
        # RandomForest usually returns a list of shap values for each class
        shap_values_class1 = shap_values[1]
    else:
        shap_values_class1 = shap_values
        
    np.save(os.path.join(results_dir, "shap_values.npy"), shap_values_class1)
    np.save(os.path.join(results_dir, "shap_base_values.npy"), explainer.expected_value)
    X_sample.to_csv(os.path.join(results_dir, "shap_X_sample.csv"), index=False)
    
    print("Explainability metrics saved to data/results/")

if __name__ == "__main__":
    generate_explanations()
