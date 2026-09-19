import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import joblib

def get_feature_sets(columns):
    evolution_features = ['code_churn', 'revision_count', 'developer_count']
    static_features = [c for c in columns if c not in evolution_features]
    return static_features, list(columns) # all features for combined

def train_models():
    processed_dir = "data/processed"
    models_dir = "src/models/saved"
    os.makedirs(models_dir, exist_ok=True)
    
    print("Loading preprocessed data...")
    X_train = pd.read_csv(os.path.join(processed_dir, "X_train.csv"))
    y_train = pd.read_csv(os.path.join(processed_dir, "y_train.csv")).values.ravel()
    
    static_features, all_features = get_feature_sets(X_train.columns)
    print(f"Static features ({len(static_features)}): {static_features}")
    print(f"Evolution features: {[c for c in all_features if c not in static_features]}")
    
    X_train_static = X_train[static_features]
    
    from sklearn.model_selection import GridSearchCV
    
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'DecisionTree': DecisionTreeClassifier(random_state=42),
        'RandomForest': RandomForestClassifier(random_state=42)
    }
    
    # Define a simple grid search for Random Forest to find the best reliable model
    rf_params = {
        'n_estimators': [50, 100],
        'max_depth': [None, 10, 20]
    }
    
    for name, model in models.items():
        print(f"Training {name} (Static Only)...")
        if name == 'RandomForest':
            # Grid search for the best RandomForest
            gs_static = GridSearchCV(model, rf_params, cv=3, scoring='f1', n_jobs=-1)
            gs_static.fit(X_train_static, y_train)
            best_static = gs_static.best_estimator_
            joblib.dump(best_static, os.path.join(models_dir, f"{name}_static.pkl"))
            
            print(f"Training {name} (Static + Evolution)...")
            gs_combined = GridSearchCV(model, rf_params, cv=3, scoring='f1', n_jobs=-1)
            gs_combined.fit(X_train, y_train)
            best_combined = gs_combined.best_estimator_
            joblib.dump(best_combined, os.path.join(models_dir, f"{name}_combined.pkl"))
            print(f"Best RF params: {gs_combined.best_params_}")
        else:
            model.fit(X_train_static, y_train)
            joblib.dump(model, os.path.join(models_dir, f"{name}_static.pkl"))
            
            print(f"Training {name} (Static + Evolution)...")
            model_combined = type(model)(**model.get_params())
            model_combined.fit(X_train, y_train)
            joblib.dump(model_combined, os.path.join(models_dir, f"{name}_combined.pkl"))

    print("Model training complete. Models saved to src/models/saved/")

if __name__ == "__main__":
    train_models()
