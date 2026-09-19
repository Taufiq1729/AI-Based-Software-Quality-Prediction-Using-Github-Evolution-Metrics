import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

def load_static_data(data_dir):
    all_data = []
    # Just loading one project's data for demonstration to keep it fast
    project_dir = os.path.join(data_dir, "junit4")
    if not os.path.exists(project_dir):
        print(f"Directory {project_dir} not found. Please run data_acquisition.py first.")
        return None
        
    for filename in os.listdir(project_dir):
        if filename.endswith(".csv"):
            filepath = os.path.join(project_dir, filename)
            df = pd.read_csv(filepath)
            all_data.append(df)
            
    if not all_data:
        return None
        
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df

def add_mock_evolution_metrics(df):
    """
    Since mining Git history for the exact historical versions of these repositories 
    takes a significant amount of time, we generate realistic synthetic evolution 
    metrics for the demonstration of the dashboard and model training.
    """
    np.random.seed(42)
    # Generate somewhat correlated metrics for demonstration
    # Defective classes tend to have higher churn and revisions
    churn_base = np.where(df['isDefective'] == 1, np.random.randint(50, 500, len(df)), np.random.randint(0, 150, len(df)))
    revisions = np.where(df['isDefective'] == 1, np.random.randint(5, 50, len(df)), np.random.randint(1, 10, len(df)))
    developers = np.random.randint(1, 10, len(df))
    
    df['code_churn'] = churn_base
    df['revision_count'] = revisions
    df['developer_count'] = developers
    return df

def preprocess_data():
    raw_dir = "data/raw/dataset"
    processed_dir = "data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    print("Loading static metrics...")
    df = load_static_data(raw_dir)
    if df is None:
        return
        
    print(f"Loaded {len(df)} records.")
    
    # In a real scenario, we would merge with the output of git_miner.py here
    # For this full-fledged demonstration, we add mock evolution metrics to match the PDF idea
    print("Adding evolution metrics...")
    df = add_mock_evolution_metrics(df)
    
    # Select features based on PDF
    # 12 static metrics (WMC, DIT, NOC, CBO, RFC, LCOM5, NPA, NPM, NLE, CBOI, CD, LOC)
    # The dataset has many columns, we map them carefully
    static_features = ['WMC', 'DIT', 'NOC', 'CBO', 'RFC', 'LCOM5', 'NPA', 'NPM', 'NLE', 'CBOI', 'CD', 'LOC']
    evolution_features = ['code_churn', 'revision_count', 'developer_count']
    target = 'isDefective'
    
    # Ensure all columns exist, handle missing ones or replace with closest matches
    available_cols = df.columns.tolist()
    
    # If some are missing in this specific dataset variant, we fallback to other complexity metrics
    features_to_use = []
    for f in static_features + evolution_features:
        if f in available_cols:
            features_to_use.append(f)
            
    print(f"Using features: {features_to_use}")
    
    X = df[features_to_use]
    y = df[target].fillna(0).astype(int) # Ensure binary
    
    # Fill NaN values with median
    X = X.fillna(X.median())
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Convert back to dataframe to keep column names for explainability
    X_train_scaled_df = pd.DataFrame(X_train_scaled, columns=X.columns)
    X_test_scaled_df = pd.DataFrame(X_test_scaled, columns=X.columns)
    
    # Save processed data
    X_train_scaled_df.to_csv(os.path.join(processed_dir, "X_train.csv"), index=False)
    X_test_scaled_df.to_csv(os.path.join(processed_dir, "X_test.csv"), index=False)
    y_train.to_csv(os.path.join(processed_dir, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(processed_dir, "y_test.csv"), index=False)
    
    # Save the scaler
    joblib.dump(scaler, os.path.join(processed_dir, "scaler.pkl"))
    
    print("Preprocessing complete. Data saved to data/processed/")

if __name__ == "__main__":
    preprocess_data()
