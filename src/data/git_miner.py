import pandas as pd
from pydriller import Repository
from collections import defaultdict
import os

def mine_evolution_metrics(repo_url, since_date=None, to_date=None):
    print(f"Mining repository: {repo_url}")
    
    # Metrics to collect per file
    metrics = defaultdict(lambda: {
        'code_churn': 0,
        'revision_count': 0,
        'developers': set()
    })
    
    try:
        repo = Repository(repo_url, since=since_date, to=to_date)
        for commit in repo.traverse_commits():
            author = commit.author.email
            for modified_file in commit.modified_files:
                filename = modified_file.filename
                if filename.endswith(".java"):
                    # Calculate code churn (lines added + lines deleted)
                    churn = modified_file.added_lines + modified_file.deleted_lines
                    
                    metrics[filename]['code_churn'] += churn
                    metrics[filename]['revision_count'] += 1
                    metrics[filename]['developers'].add(author)
                    
    except Exception as e:
        print(f"Error mining {repo_url}: {e}")
        
    # Convert sets to counts and prepare dataframe
    records = []
    for filename, data in metrics.items():
        records.append({
            'filename': filename,
            'code_churn': data['code_churn'],
            'revision_count': data['revision_count'],
            'developer_count': len(data['developers'])
        })
        
    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    # Example usage for a single small project
    REPO_URL = "https://github.com/apache/commons-math.git"
    print("Starting git mining... (this may take a while depending on repository size)")
    df_metrics = mine_evolution_metrics(REPO_URL)
    os.makedirs("data/processed", exist_ok=True)
    df_metrics.to_csv("data/processed/commons_math_evolution.csv", index=False)
    print("Evolution metrics saved to data/processed/commons_math_evolution.csv")
