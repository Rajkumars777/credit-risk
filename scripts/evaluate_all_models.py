# -*- coding: utf-8 -*-
"""
evaluate_all_models.py
======================
Full model performance evaluation across all 3 credit scoring models.
Computes: Confusion Matrix, Accuracy, Precision, Recall, F1, Specificity,
          AUC-ROC, AUC-PR, Brier Score, KS Statistic, Gini Coefficient.
Ground Truth: Actual DPD > 1 = true default (label = 1).
"""

import pandas as pd
import numpy as np
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    confusion_matrix, classification_report
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path("c:/Users/rajak/Videos/ltid-oct/credit-scoring-app")

MODELS = {
    "Before Fix (5a5a)": {
        "csv":       BASE / "credit-scoring-app-commitid-5a5a/result_5a5a.csv",
        "threshold": 0.4082,
    },
    "After Fix": {
        "csv":       BASE / "result_corrected.csv",
        "threshold": 0.2353,
    },
    "DPD 0": {
        "csv":       BASE / "output dpd 0/result_dpd0.csv",
        "threshold": 0.2939,
    },
}

SEP = "=" * 80

def evaluate(name, cfg):
    df = pd.read_csv(cfg["csv"])
    threshold = cfg["threshold"]

    # ── Ground truth ──────────────────────────────────────────────────────────
    y_true = (df["Actual DPD"].astype(float) > 1).astype(int)
    y_prob  = df["Predicted Risk"].astype(float)
    y_pred  = df["Prediction"].astype(int)  # already thresholded at model's own threshold

    total   = len(df)
    n_pos   = y_true.sum()   # actual defaults
    n_neg   = total - n_pos  # actual non-defaults

    # ── Confusion Matrix ──────────────────────────────────────────────────────
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    # ── Core Metrics ─────────────────────────────────────────────────────────
    accuracy    = (tp + tn) / total
    precision   = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall      = tp / (tp + fn) if (tp + fn) > 0 else 0.0   # sensitivity
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1          = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr         = fp / (fp + tn) if (fp + tn) > 0 else 0.0   # false positive rate

    # ── Probability-Based Metrics ─────────────────────────────────────────────
    auc_roc = roc_auc_score(y_true, y_prob)
    auc_pr  = average_precision_score(y_true, y_prob)
    brier   = brier_score_loss(y_true, y_prob)
    gini    = 2 * auc_roc - 1

    # ── KS Statistic (max separation between TPR and FPR curves) ─────────────
    from sklearn.metrics import roc_curve
    fpr_arr, tpr_arr, _ = roc_curve(y_true, y_prob)
    ks_stat = float(np.max(tpr_arr - fpr_arr))

    # ── High Risk Tier Counts ─────────────────────────────────────────────────
    hr_count   = int((df["Risk Tier"] == "High Risk").sum())
    hr_caught  = int(((df["Risk Tier"] == "High Risk") & (y_true == 1)).sum())
    hr_missed  = int(((df["Risk Tier"] != "High Risk") & (y_true == 1)).sum())
    hr_false   = int(((df["Risk Tier"] == "High Risk") & (y_true == 0)).sum())  # false alarms
    hr_recall  = hr_caught / n_pos if n_pos > 0 else 0.0

    print(SEP)
    print(f"  MODEL: {name}")
    print(SEP)
    print(f"  Total records evaluated   : {total:,}")
    print(f" Actual defaults (DPD>1)  : {n_pos:,}  ({n_pos/total*100:.2f}%)")
    print(f"  Decision Threshold        : {threshold:.4f}  ({threshold*100:.2f}%)")
    print()
    print(f"  +------------------------------------------+")
    print(f"  |          CONFUSION MATRIX                |")
    print(f"  |                                          |")
    print(f"  |  Actual\\Predicted   Default   Non-Def   |")
    print(f"  |  Actual Default  -> {tp:>7,}   {fn:>7,}  | (TP / FN)")
    print(f"  |  Actual Non-Def  -> {fp:>7,}   {tn:>7,}  | (FP / TN)")
    print(f"  +------------------------------------------+")
    print()
    print(f"  ── Classification Metrics ──────────────────────────")
    print(f"  Accuracy         : {accuracy*100:6.2f}%")
    print(f"  Precision        : {precision*100:6.2f}%  (of predicted defaults, how many were real)")
    print(f"  Recall/Sensitivity: {recall*100:6.2f}%  (of real defaults, how many we caught)")
    print(f"  Specificity      : {specificity*100:6.2f}%  (of real non-defaults, how many we correctly cleared)")
    print(f"  F1 Score         : {f1*100:6.2f}%  (harmonic mean of precision & recall)")
    print(f"  False Positive Rate: {fpr*100:6.2f}%  (% of good borrowers wrongly flagged)")
    print()
    print(f"  ── Probability / Ranking Metrics ───────────────────")
    print(f"  AUC-ROC          : {auc_roc:.4f}  (1.0 = perfect, 0.5 = random)")
    print(f"  Gini Coefficient : {gini:.4f}  (2×AUC-ROC − 1, industry standard)")
    print(f"  AUC-PR           : {auc_pr:.4f}  (area under precision-recall curve)")
    print(f"  Brier Score      : {brier:.4f}  (probability calibration, lower = better)")
    print(f"  KS Statistic     : {ks_stat:.4f}  (max TPR-FPR separation, >0.40 is good)")
    print()
    print(f"  ── High Risk Tier Validation ────────────────────────")
    print(f"  High Risk flagged        : {hr_count:,}")
    print(f"  True Defaults caught     : {hr_caught:,}  ({hr_recall*100:.2f}% recall of all defaults)")
    print(f"  True Defaults missed     : {hr_missed:,}")
    print(f"  False Alarms (FP)        : {hr_false:,}  (good borrowers wrongly in High Risk)")
    print()

    return {
        "Model": name,
        "Records": total,
        "True Defaults": n_pos,
        "Threshold": threshold,
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "Specificity": specificity,
        "F1": f1,
        "AUC-ROC": auc_roc,
        "Gini": gini,
        "AUC-PR": auc_pr,
        "Brier": brier,
        "KS": ks_stat,
        "High Risk Count": hr_count,
        "HR True Catches": hr_caught,
        "HR Missed Defaults": hr_missed,
        "HR False Alarms": hr_false,
        "HR Recall": hr_recall,
    }


print("\n")
print(SEP)
print("  CREDIT SCORING MODEL — FULL PERFORMANCE EVALUATION")
print("  Ground Truth: Actual DPD > 1 = True Default")
print(SEP)
print()

results = []
for model_name, cfg in MODELS.items():
    r = evaluate(model_name, cfg)
    results.append(r)

# ── Side-by-side comparison table ─────────────────────────────────────────────
print(SEP)
print("  SIDE-BY-SIDE COMPARISON")
print(SEP)

metrics = [
    ("Records",          "Records",          ",d",    ""),
    ("True Defaults",    "True Defaults",    ",d",    ""),
    ("Threshold",        "Threshold",        ".4f",   ""),
    ("TP",               "True Positives",   ",d",    ""),
    ("FP",               "False Positives",  ",d",    ""),
    ("TN",               "True Negatives",   ",d",    ""),
    ("FN",               "False Negatives",  ",d",    ""),
    ("Accuracy",         "Accuracy",         ".2%",   ""),
    ("Precision",        "Precision",        ".2%",   ""),
    ("Recall",           "Recall (Sensitivity)", ".2%", ""),
    ("Specificity",      "Specificity",      ".2%",   ""),
    ("F1",               "F1 Score",         ".4f",   ""),
    ("AUC-ROC",          "AUC-ROC",          ".4f",   "★ higher = better"),
    ("Gini",             "Gini Coefficient", ".4f",   "★ industry standard"),
    ("AUC-PR",           "AUC-PR",           ".4f",   ""),
    ("Brier",            "Brier Score",      ".4f",   "★ lower = better"),
    ("KS",               "KS Statistic",     ".4f",   ">0.40 is good"),
    ("High Risk Count",  "High Risk Flagged",",d",    ""),
    ("HR True Catches",  "Defaults Caught",  ",d",    ""),
    ("HR Missed Defaults","Defaults Missed", ",d",    ""),
    ("HR False Alarms",  "False Alarms",     ",d",    ""),
    ("HR Recall",        "HR Recall %",      ".2%",   ""),
]

col_w = 30
val_w = 22
header = f"  {'Metric':<{col_w}}" + "".join(f"{r['Model']:<{val_w}}" for r in results)
print(header)
print("  " + "-" * (col_w + val_w * len(results)))
for key, label, fmt, note in metrics:
    row = f"  {label:<{col_w}}"
    for r in results:
        v = r[key]
        try:
            row += f"{format(v, fmt):<{val_w}}"
        except Exception:
            row += f"{str(v):<{val_w}}"
    if note:
        row += f"  ← {note}"
    print(row)

print()
print(SEP)
print("  VERDICT")
print(SEP)
