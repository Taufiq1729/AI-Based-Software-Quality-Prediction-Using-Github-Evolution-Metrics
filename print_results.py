import json
d = json.load(open('data/results/evaluation_metrics.json'))
for model, sets in d.items():
    for fs, r in sets.items():
        cm = r['ConfusionMatrix']
        print(f"{model} | {fs}:")
        print(f"  Acc={r['Accuracy']:.4f} | Bal.Acc={r['Balanced_Accuracy']:.4f} | Prec={r['Precision']:.4f} | Recall={r['Recall']:.4f} | F1={r['F1_Score']:.4f} | ROC-AUC={r['ROC_AUC']:.4f} | PR-AUC={r['PR_AUC']:.4f}")
        print(f"  ConfusionMatrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
        print()

