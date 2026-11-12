    import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.backend.ai_model import AIModel
from src.frontend.main import App
from lightgbm import LGBMClassifier
from sklearn.metrics import confusion_matrix, roc_auc_score, f1_score, precision_score, recall_score, average_precision_score

print("Loading datasets...")
df_may = pd.read_excel(PROJECT_ROOT / "src/data/May 12 Status Contracts.xlsx")
df_ext = pd.read_excel(PROJECT_ROOT / "src/data/Extracted New.xlsx")
df_2026 = pd.read_excel(PROJECT_ROOT / "src/data/Raw Jan - Jun 2026.xlsx")

ui = App.__new__(App)
helper_model = AIModel("src/data/May 12 Status Contracts.xlsx", "src/data/Extracted New.xlsx")
features = helper_model.features

print("Preprocessing rows...")
rows_may = [ui._row_to_ai_features(ui._normalize_input_row(r)) for r in df_may.to_dict(orient="records")]
rows_2026 = [ui._row_to_ai_features(ui._normalize_input_row(r)) for r in df_2026.to_dict(orient="records")]

raw_df_may = pd.DataFrame(rows_may)
raw_df_2026 = pd.DataFrame(rows_2026)

frame_may = helper_model.process_data(raw_df_may, inference=True)
encoded_may = helper_model._encode_processed_harish_input(frame_may)[features]

frame_2026 = helper_model.process_data(raw_df_2026, inference=True)
encoded_2026 = helper_model._encode_processed_harish_input(frame_2026)[features]

obs_may = pd.to_numeric(df_may["Current DPD"], errors="coerce").fillna(0)
obs_2026 = pd.to_numeric(df_2026["Current DPD"], errors="coerce").fillna(0)
y_2026 = (obs_2026 > 10.0).astype(int).to_numpy()

# Also let's prepare combined May 12 + Extracted New
rows_ext = [ui._row_to_ai_features(ui._normalize_input_row(r)) for r in df_ext.to_dict(orient="records")]
raw_df_ext = pd.DataFrame(rows_ext)
frame_ext = helper_model.process_data(raw_df_ext, inference=True)
encoded_ext = helper_model._encode_processed_harish_input(frame_ext)[features]
obs_ext = pd.to_numeric(df_ext["Current DPD"], errors="coerce").fillna(0)

encoded_combined = pd.concat([encoded_may, encoded_ext], ignore_index=True)
obs_combined = pd.concat([obs_may, obs_ext], ignore_index=True)

experiments = [
    {
        "desc": "May 12 ONLY | Target DPD > 0 | scale_pos_weight=2.5",
        "X": encoded_may,
        "y": (obs_may > 0.0).astype(int).to_numpy(),
        "params": {"n_estimators": 500, "learning_rate": 0.02, "num_leaves": 48, "max_depth": 7, "min_child_samples": 30, "subsample": 0.85, "colsample_bytree": 0.70, "scale_pos_weight": 2.5, "reg_alpha": 1.0, "reg_lambda": 3.0, "random_state": 42, "verbose": -1}
    },
    {
        "desc": "May 12 ONLY | Target DPD > 10 | scale_pos_weight=2.8 | Tuned",
        "X": encoded_may,
        "y": (obs_may > 10.0).astype(int).to_numpy(),
        "params": {"n_estimators": 600, "learning_rate": 0.02, "num_leaves": 48, "max_depth": 7, "min_child_samples": 35, "subsample": 0.85, "colsample_bytree": 0.70, "scale_pos_weight": 2.8, "reg_alpha": 1.5, "reg_lambda": 4.0, "random_state": 42, "verbose": -1}
    },
    {
        "desc": "May 12 ONLY | Target DPD > 5 | scale_pos_weight=2.5",
        "X": encoded_may,
        "y": (obs_may > 5.0).astype(int).to_numpy(),
        "params": {"n_estimators": 500, "learning_rate": 0.02, "num_leaves": 48, "max_depth": 7, "min_child_samples": 30, "subsample": 0.85, "colsample_bytree": 0.70, "scale_pos_weight": 2.5, "reg_alpha": 1.0, "reg_lambda": 3.0, "random_state": 42, "verbose": -1}
    },
    {
        "desc": "May 12 + Extracted New | Target DPD > 10 | scale_pos_weight=2.5",
        "X": encoded_combined,
        "y": (obs_combined > 10.0).astype(int).to_numpy(),
        "params": {"n_estimators": 600, "learning_rate": 0.02, "num_leaves": 48, "max_depth": 7, "min_child_samples": 40, "subsample": 0.85, "colsample_bytree": 0.70, "scale_pos_weight": 2.5, "reg_alpha": 1.5, "reg_lambda": 4.0, "random_state": 42, "verbose": -1}
    },
    {
        "desc": "May 12 + Extracted New | Target DPD > 0 | scale_pos_weight=2.0",
        "X": encoded_combined,
        "y": (obs_combined > 0.0).astype(int).to_numpy(),
        "params": {"n_estimators": 600, "learning_rate": 0.02, "num_leaves": 48, "max_depth": 7, "min_child_samples": 40, "subsample": 0.85, "colsample_bytree": 0.70, "scale_pos_weight": 2.0, "reg_alpha": 1.5, "reg_lambda": 4.0, "random_state": 42, "verbose": -1}
    },
]

for exp in experiments:
    print(f"\n==========================================")
    print(f"Running: {exp['desc']}")
    clf = LGBMClassifier(**exp["params"])
    clf.fit(exp["X"], exp["y"])
    
    # 1. Pure ML probabilities
    probs_raw = clf.predict_proba(encoded_2026)[:, 1]
    auc_raw = roc_auc_score(y_2026, probs_raw)
    pr_auc_raw = average_precision_score(y_2026, probs_raw)
    print(f"Pure ML Out-of-Time ROC-AUC: {auc_raw:.4f} | PR-AUC: {pr_auc_raw:.4f}")
    
    # 2. With Underwriting Policy Overlay
    probs_policy = helper_model._apply_underwriting_policy_layer(raw_df_2026, probs_raw)
    auc_policy = roc_auc_score(y_2026, probs_policy)
    pr_auc_policy = average_precision_score(y_2026, probs_policy)
    print(f"With Policy Overlay ROC-AUC: {auc_policy:.4f} | PR-AUC: {pr_auc_policy:.4f}")
    
    for name, p in [("Pure ML", probs_raw), ("ML + Policy Overlay", probs_policy)]:
        print(f"  --- {name} Threshold Evaluation ---")
        for th in [0.18, 0.20, 0.22, 0.25, 0.30, 0.35, 0.40]:
            preds = (p >= th).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_2026, preds).ravel()
            rec = recall_score(y_2026, preds)
            spec = tn / (tn + fp)
            prec = precision_score(y_2026, preds, zero_division=0)
            f1 = f1_score(y_2026, preds, zero_division=0)
            print(f"    Th={th:.2f} | TP={tp:3d} FN={fn:3d} FP={fp:4d} TN={tn:4d} | Rec={rec*100:5.2f}% Spec={spec*100:5.2f}% Prec={prec*100:5.2f}% F1={f1:.4f}")
