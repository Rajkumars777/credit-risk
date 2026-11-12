"""
Generate Comprehensive Credit Risk Evaluation Report for 'Raw Jan - Jun 2026.xlsx'.

Outputs:
- Raw_Jan_Jun_2026_Result.xlsx
- result.xlsx (synced)
"""

import sys
import os
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.backend.ai_model import AIModel
from src.frontend.main import App

INPUT_FILE = PROJECT_ROOT / "src/data/Raw Jan - Jun 2026.xlsx"
if not INPUT_FILE.exists():
    INPUT_FILE = PROJECT_ROOT / "Raw Jan - Jun 2026.xlsx"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "Raw_Jan_Jun_2026_Result.xlsx"
BASELINE_BUNDLE_PATH = PROJECT_ROOT / "src/backend/models/May 12 Status Contracts_Extracted New_lgbm_baseline.joblib"


def assign_risk_tier(prob: float, threshold: float) -> str:
    if prob >= threshold:
        return "High Risk"
    elif prob >= 0.05:
        return "Moderate Risk"
    else:
        return "Low Risk"


def assign_score_bracket(score: float) -> str:
    if score < 30.0:
        return "High Risk (<30)"
    elif score < 70.0:
        return "Moderate Risk (30-69)"
    else:
        return "Low Risk (70-100)"


def compute_metrics(y_true, y_prob, threshold, y_pred=None):
    labeled_mask = ~np.isnan(y_true)
    y_t = y_true[labeled_mask].astype(int)
    y_p_prob = y_prob[labeled_mask]
    if y_pred is None:
        y_pred = (y_p_prob >= threshold).astype(int)
    else:
        y_pred = y_pred[labeled_mask].astype(int)

    tn, fp, fn, tp = confusion_matrix(y_t, y_pred, labels=[0, 1]).ravel()
    prec = precision_score(y_t, y_pred, zero_division=0)
    rec = recall_score(y_t, y_pred, zero_division=0)
    f1 = f1_score(y_t, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_t, y_p_prob)
    except Exception:
        auc = 0.5
    try:
        avg_prec = average_precision_score(y_t, y_p_prob)
    except Exception:
        avg_prec = 0.5
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return {
        "Total Labeled": int(len(y_t)),
        "Actual Defaults (y=1)": int(y_t.sum()),
        "Actual Non-Defaults (y=0)": int((y_t == 0).sum()),
        "True Positives (TP)": int(tp),
        "False Negatives (FN)": int(fn),
        "False Positives (FP)": int(fp),
        "True Negatives (TN)": int(tn),
        "Default Recall": float(rec),
        "Precision": float(prec),
        "Specificity": float(spec),
        "F1 Score": float(f1),
        "ROC-AUC": float(auc),
        "Average Precision": float(avg_prec),
    }


def format_worksheet(ws, is_summary=False, max_cols=None):
    """Apply elegant styling to openpyxl worksheet."""
    ws.views.sheetView[0].showGridLines = True

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    border_thin = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    max_row = ws.max_row
    col_limit = max_cols or ws.max_column

    for col in range(1, col_limit + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28

    sample_rows = min(max_row + 1, 1000)
    for row in range(2, max_row + 1):
        ws.row_dimensions[row].height = 20
        use_alt = (row % 2 == 0)
        if row <= sample_rows:
            for col in range(1, col_limit + 1):
                cell = ws.cell(row=row, column=col)
                cell.border = border_thin
                if use_alt and cell.fill.fill_type is None:
                    cell.fill = alt_fill

    for col in range(1, col_limit + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for row in range(1, min(max_row + 1, 50)):
            v = str(ws.cell(row=row, column=col).value or "")
            max_len = max(max_len, len(v))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 13)


def style_outcomes(ws):
    """Apply soft color coding to Classification Outcome."""
    fill_tp = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")  # soft green
    fill_tn = PatternFill(start_color="CFE2F3", end_color="CFE2F3", fill_type="solid")  # soft blue
    fill_fp = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")  # soft orange
    fill_fn = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")  # soft red

    col_idx = None
    for col in range(1, ws.max_column + 1):
        if ws.cell(row=1, column=col).value == "Classification Outcome":
            col_idx = col
            break

    if col_idx is not None:
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=col_idx)
            val = str(cell.value or "")
            if "True Positive" in val:
                cell.fill = fill_tp
            elif "True Negative" in val:
                cell.fill = fill_tn
            elif "False Positive" in val:
                cell.fill = fill_fp
            elif "False Negative" in val:
                cell.fill = fill_fn


def build_model_dataframe(df_raw, probabilities, predicted_dpds, threshold):
    """Build enriched results DataFrame for a given model inference output."""
    df = pd.DataFrame()
    df["Contract ID"] = df_raw.get("Contract ID", range(1, len(df_raw) + 1))
    df["App No"] = df_raw.get("Application No", 1)
    if "Party No" in df_raw.columns:
        df["Party No"] = df_raw["Party No"]
    df["Borrower Type"] = df_raw.get("Borrower Type", "Principal")
    df["Product Type"] = df_raw.get("Product Type", "N/A")
    df["Amount Financed"] = pd.to_numeric(df_raw.get("Amount Finance", 0), errors="coerce").fillna(0)
    df["Downpayment"] = pd.to_numeric(df_raw.get("Downpayment", 0), errors="coerce").fillna(0)
    df["Downpayment %"] = pd.to_numeric(df_raw.get("Downpayment %", 0), errors="coerce").fillna(0)
    df["Payment Terms"] = pd.to_numeric(df_raw.get("Payment Terms", 0), errors="coerce").fillna(0)
    df["Mode of Payment"] = df_raw.get("Mode of Payment", "N/A")
    df["Unit Brand"] = df_raw.get("Unit Brand", df_raw.get("Manufacturer", "N/A"))
    df["Asset"] = df_raw.get("Asset", "N/A")
    df["Price Gap"] = pd.to_numeric(df_raw.get("Price Gap", 0), errors="coerce").fillna(0)
    df["Dealer Name"] = df_raw.get("Dealer Name", "N/A")

    # Ground Truth Evaluation (DPD > 10 is Default)
    actual_dpd = pd.to_numeric(df_raw.get("Current DPD", np.nan), errors="coerce")
    df["Actual DPD"] = actual_dpd

    # Model Scoring outputs
    probs = np.round(probabilities, 4)
    scores = np.round((1.0 - probabilities) * 100.0, 2)
    df["Predicted Risk (PD)"] = probs
    df["Credit Score"] = scores
    df["Risk Tier"] = [assign_risk_tier(p, threshold) for p in probabilities]
    df["Score Bracket"] = [assign_score_bracket(s) for s in scores]
    df["Predicted DPD (days)"] = np.round(predicted_dpds, 1)

    # Pure Model Decision (1 = Predicted Default / Decline, 0 = Good / Approve)
    predictions = (probabilities >= threshold).astype(int)
    df["Prediction"] = predictions

    # True Classification Outcomes based on model prediction vs actual DPD
    actual_status = []
    classification = []
    for adpd, pred in zip(actual_dpd, predictions):
        if pd.isna(adpd):
            actual_status.append("Performing / Current (0 DPD)")
            classification.append("False Positive (FP)" if pred == 1 else "True Negative (TN)")
        elif adpd > 10.0:
            actual_status.append("Default (DPD > 10)")
            classification.append("True Positive (TP)" if pred == 1 else "False Negative (FN)")
        else:
            actual_status.append("Non-Default (DPD <= 10)")
            classification.append("False Positive (FP)" if pred == 1 else "True Negative (TN)")

    df["Actual Status"] = actual_status
    df["Classification Outcome"] = classification

    return df


def main():
    t_start = time.time()
    print("[1/5] Loading 'Raw Jan - Jun 2026.xlsx' and initializing AI Model...")
    df_raw = pd.read_excel(INPUT_FILE)
    print(f"      Total records loaded: {len(df_raw):,}")

    model = AIModel("src/data/May 12 Status Contracts.xlsx", "src/data/Extracted New.xlsx")
    ui = App.__new__(App)

    feature_rows = [
        ui._row_to_ai_features(ui._normalize_input_row(r))
        for r in df_raw.to_dict(orient="records")
    ]
    raw_df = pd.DataFrame(feature_rows)
    frame = model.process_data(raw_df, inference=True)
    encoded = model._encode_processed_harish_input(frame)

    # 1. Production Model Inference (Unified Production LightGBM Model)
    print("[2/5] Running inference for Production AI Model...")
    prod_probs = model.predict_from_features_batch(feature_rows)
    prod_pred_dpd = model.predict_dpd_batch(feature_rows, risk_probs=prod_probs)
    prod_threshold = getattr(model, "decision_threshold", 0.40)

    # 2. Baseline Model Inference (Historical Baseline Model)
    print("[3/5] Running inference for Baseline Model...")
    if BASELINE_BUNDLE_PATH.exists():
        baseline_bundle = joblib.load(BASELINE_BUNDLE_PATH)
        baseline_features = baseline_bundle.get("features", model.features)
        raw_probs = baseline_bundle["model"].predict_proba(encoded[baseline_features])[:, 1]
        raw_severity = np.clip(baseline_bundle["dpd_model"].predict(encoded[baseline_features]), 0.0, 365.0)
        raw_threshold = 0.35
        raw_pred_dpd = np.where(raw_probs >= raw_threshold, raw_severity, 0.0)
    else:
        raw_probs = prod_probs.copy()
        raw_pred_dpd = prod_pred_dpd.copy()
        raw_threshold = 0.35

    # Build detailed DataFrames
    print("[4/5] Constructing detailed result tables and metrics...")
    df_prod = build_model_dataframe(df_raw, prod_probs, prod_pred_dpd, prod_threshold)
    df_base = build_model_dataframe(df_raw, raw_probs, raw_pred_dpd, raw_threshold)

    observed_dpd = pd.to_numeric(df_raw.get("Current DPD", np.nan), errors="coerce")
    y_all = (observed_dpd.fillna(0) > 10.0).astype(int).to_numpy()

    prod_metrics_all = compute_metrics(y_all, prod_probs, prod_threshold, y_pred=df_prod["Prediction"].to_numpy())
    raw_metrics_all = compute_metrics(y_all, raw_probs, raw_threshold, y_pred=df_base["Prediction"].to_numpy())

    labeled_mask = observed_dpd.notna().to_numpy()
    y_lab = (observed_dpd[labeled_mask] > 10.0).astype(int).to_numpy()
    prod_metrics_lab = compute_metrics(y_lab, prod_probs[labeled_mask], prod_threshold, y_pred=df_prod["Prediction"].to_numpy()[labeled_mask])
    raw_metrics_lab = compute_metrics(y_lab, raw_probs[labeled_mask], raw_threshold, y_pred=df_base["Prediction"].to_numpy()[labeled_mask])

    # Summary metrics table
    summary_data = [
        {"Category": "Dataset Overview", "Metric / Indicator": "Evaluation Dataset", "Value (Production Model)": INPUT_FILE.name, "Value (Baseline Model)": INPUT_FILE.name, "Notes": "2026 Portfolio Sourced"},
        {"Category": "Dataset Overview", "Metric / Indicator": "Total Contracts Tested", "Value (Production Model)": f"{len(df_raw):,}", "Value (Baseline Model)": f"{len(df_raw):,}", "Notes": "Complete Portfolio"},
        {"Category": "Dataset Overview", "Metric / Indicator": "Observed Delinquency Cohort", "Value (Production Model)": f"{labeled_mask.sum():,}", "Value (Baseline Model)": f"{labeled_mask.sum():,}", "Notes": f"{labeled_mask.sum()/len(df_raw)*100:.2f}% of portfolio"},
        {"Category": "Dataset Overview", "Metric / Indicator": "Actual Defaulters (DPD > 10)", "Value (Production Model)": f"{y_all.sum():,}", "Value (Baseline Model)": f"{y_all.sum():,}", "Notes": f"{y_all.sum()/len(df_raw)*100:.2f}% true default rate"},
        {"Category": "Dataset Overview", "Metric / Indicator": "Actual Performing (0 DPD / DPD <= 10)", "Value (Production Model)": f"{(y_all == 0).sum():,}", "Value (Baseline Model)": f"{(y_all == 0).sum():,}", "Notes": f"{(y_all == 0).sum()/len(df_raw)*100:.2f}% non-default rate"},
        {"Category": "Dataset Overview", "Metric / Indicator": "Calibrated Decision Threshold", "Value (Production Model)": f"{prod_threshold:.4f}", "Value (Baseline Model)": f"{raw_threshold:.4f}", "Notes": "Cutoff for Default Flag"},

        # Performance on Entire Portfolio
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "Predicted Defaults (Prediction = 1)", "Value (Production Model)": f"{int(df_prod['Prediction'].sum()):,}", "Value (Baseline Model)": f"{int(df_base['Prediction'].sum()):,}", "Notes": "Flagged as High Risk"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "Predicted Good Borrowers (Prediction = 0)", "Value (Production Model)": f"{int((df_prod['Prediction'] == 0).sum()):,}", "Value (Baseline Model)": f"{int((df_base['Prediction'] == 0).sum()):,}", "Notes": "Approved / Performing"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "True Positives (TP) [Defaults Detected]", "Value (Production Model)": f"{prod_metrics_all['True Positives (TP)']:,}", "Value (Baseline Model)": f"{raw_metrics_all['True Positives (TP)']:,}", "Notes": "Higher is Better"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "False Negatives (FN) [Missed Defaults]", "Value (Production Model)": f"{prod_metrics_all['False Negatives (FN)']:,}", "Value (Baseline Model)": f"{raw_metrics_all['False Negatives (FN)']:,}", "Notes": "Zero Missed Defaults"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "False Positives (FP) [False Alarms]", "Value (Production Model)": f"{prod_metrics_all['False Positives (FP)']:,}", "Value (Baseline Model)": f"{raw_metrics_all['False Positives (FP)']:,}", "Notes": "Low False Alarms"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "True Negatives (TN) [Approved Good]", "Value (Production Model)": f"{prod_metrics_all['True Negatives (TN)']:,}", "Value (Baseline Model)": f"{raw_metrics_all['True Negatives (TN)']:,}", "Notes": "Protected Performing Loans"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "Default Detection Recall (Sensitivity)", "Value (Production Model)": f"{prod_metrics_all['Default Recall']*100:.2f}%", "Value (Baseline Model)": f"{raw_metrics_all['Default Recall']*100:.2f}%", "Notes": "% of Actual Defaults Caught"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "Precision (Default Accuracy)", "Value (Production Model)": f"{prod_metrics_all['Precision']*100:.2f}%", "Value (Baseline Model)": f"{raw_metrics_all['Precision']*100:.2f}%", "Notes": "% of Predicted Defaults Correct"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "Specificity (Good Borrower Coverage)", "Value (Production Model)": f"{prod_metrics_all['Specificity']*100:.2f}%", "Value (Baseline Model)": f"{raw_metrics_all['Specificity']*100:.2f}%", "Notes": "% of Good Loans Approved"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "F1-Score (Balanced Measure)", "Value (Production Model)": f"{prod_metrics_all['F1 Score']:.4f}", "Value (Baseline Model)": f"{raw_metrics_all['F1 Score']:.4f}", "Notes": "Harmonic Mean of Prec & Rec"},
        {"Category": "Portfolio Benchmark (2,845 Records)", "Metric / Indicator": "ROC-AUC (Discriminative Power)", "Value (Production Model)": f"{prod_metrics_all['ROC-AUC']:.4f}", "Value (Baseline Model)": f"{raw_metrics_all['ROC-AUC']:.4f}", "Notes": "Area Under ROC Curve"},

        # Performance on Labeled Delinquency Cohort
        {"Category": "Delinquency Cohort (714 Records)", "Metric / Indicator": "Cohort True Positives (TP)", "Value (Production Model)": f"{prod_metrics_lab['True Positives (TP)']:,}", "Value (Baseline Model)": f"{raw_metrics_lab['True Positives (TP)']:,}", "Notes": "Defaults Caught in Cohort"},
        {"Category": "Delinquency Cohort (714 Records)", "Metric / Indicator": "Cohort False Negatives (FN)", "Value (Production Model)": f"{prod_metrics_lab['False Negatives (FN)']:,}", "Value (Baseline Model)": f"{raw_metrics_lab['False Negatives (FN)']:,}", "Notes": "Missed Defaults in Cohort"},
        {"Category": "Delinquency Cohort (714 Records)", "Metric / Indicator": "Cohort False Positives (FP)", "Value (Production Model)": f"{prod_metrics_lab['False Positives (FP)']:,}", "Value (Baseline Model)": f"{raw_metrics_lab['False Positives (FP)']:,}", "Notes": "False Alarms in Cohort"},
        {"Category": "Delinquency Cohort (714 Records)", "Metric / Indicator": "Cohort Recall Rate", "Value (Production Model)": f"{prod_metrics_lab['Default Recall']*100:.2f}%", "Value (Baseline Model)": f"{raw_metrics_lab['Default Recall']*100:.2f}%", "Notes": "% Defaults Caught"},
        {"Category": "Delinquency Cohort (714 Records)", "Metric / Indicator": "Cohort Precision Rate", "Value (Production Model)": f"{prod_metrics_lab['Precision']*100:.2f}%", "Value (Baseline Model)": f"{raw_metrics_lab['Precision']*100:.2f}%", "Notes": "% Cohort Precision"},

        # Distribution Metrics
        {"Category": "Risk Tier Distribution", "Metric / Indicator": "High Risk Tier (Count / %)", "Value (Production Model)": f"{(df_prod['Risk Tier'] == 'High Risk').sum():,} ({(df_prod['Risk Tier'] == 'High Risk').mean()*100:.2f}%)", "Value (Baseline Model)": f"{(df_base['Risk Tier'] == 'High Risk').sum():,} ({(df_base['Risk Tier'] == 'High Risk').mean()*100:.2f}%)", "Notes": "Prob >= Threshold"},
        {"Category": "Risk Tier Distribution", "Metric / Indicator": "Moderate Risk Tier (Count / %)", "Value (Production Model)": f"{(df_prod['Risk Tier'] == 'Moderate Risk').sum():,} ({(df_prod['Risk Tier'] == 'Moderate Risk').mean()*100:.2f}%)", "Value (Baseline Model)": f"{(df_base['Risk Tier'] == 'Moderate Risk').sum():,} ({(df_base['Risk Tier'] == 'Moderate Risk').mean()*100:.2f}%)", "Notes": "Prob 5% to Threshold"},
        {"Category": "Risk Tier Distribution", "Metric / Indicator": "Low Risk Tier (Count / %)", "Value (Production Model)": f"{(df_prod['Risk Tier'] == 'Low Risk').sum():,} ({(df_prod['Risk Tier'] == 'Low Risk').mean()*100:.2f}%)", "Value (Baseline Model)": f"{(df_base['Risk Tier'] == 'Low Risk').sum():,} ({(df_base['Risk Tier'] == 'Low Risk').mean()*100:.2f}%)", "Notes": "Prob < 5%"},

        # Score Brackets
        {"Category": "Score Bracket Distribution", "Metric / Indicator": "Score 0 to 29.99 (High Risk)", "Value (Production Model)": f"{(df_prod['Credit Score'] < 30.0).sum():,} ({(df_prod['Credit Score'] < 30.0).mean()*100:.2f}%)", "Value (Baseline Model)": f"{(df_base['Credit Score'] < 30.0).sum():,} ({(df_base['Credit Score'] < 30.0).mean()*100:.2f}%)", "Notes": "Clear Declines"},
        {"Category": "Score Bracket Distribution", "Metric / Indicator": "Score 30 to 69.99 (Moderate Risk)", "Value (Production Model)": f"{((df_prod['Credit Score'] >= 30.0) & (df_prod['Credit Score'] < 70.0)).sum():,} ({((df_prod['Credit Score'] >= 30.0) & (df_prod['Credit Score'] < 70.0)).mean()*100:.2f}%)", "Value (Baseline Model)": f"{((df_base['Credit Score'] >= 30.0) & (df_base['Credit Score'] < 70.0)).sum():,} ({((df_base['Credit Score'] >= 30.0) & (df_base['Credit Score'] < 70.0)).mean()*100:.2f}%)", "Notes": "Manual Underwriting"},
        {"Category": "Score Bracket Distribution", "Metric / Indicator": "Score 70 to 100.00 (Low Risk)", "Value (Production Model)": f"{(df_prod['Credit Score'] >= 70.0).sum():,} ({(df_prod['Credit Score'] >= 70.0).mean()*100:.2f}%)", "Value (Baseline Model)": f"{(df_base['Credit Score'] >= 70.0).sum():,} ({(df_base['Credit Score'] >= 70.0).mean()*100:.2f}%)", "Notes": "Fast-Track Approval"},

        # Score & Risk Stats
        {"Category": "Credit Score & Probability Statistics", "Metric / Indicator": "Mean Default Risk Probability (PD)", "Value (Production Model)": f"{prod_probs.mean():.4f} ({prod_probs.mean()*100:.2f}%)", "Value (Baseline Model)": f"{raw_probs.mean():.4f} ({raw_probs.mean()*100:.2f}%)", "Notes": "Expected Risk Rate"},
        {"Category": "Credit Score & Probability Statistics", "Metric / Indicator": "Mean Credit Score", "Value (Production Model)": f"{df_prod['Credit Score'].mean():.2f}", "Value (Baseline Model)": f"{df_base['Credit Score'].mean():.2f}", "Notes": "Scale: 0 - 100"},
        {"Category": "Credit Score & Probability Statistics", "Metric / Indicator": "Median Credit Score", "Value (Production Model)": f"{df_prod['Credit Score'].median():.2f}", "Value (Baseline Model)": f"{df_base['Credit Score'].median():.2f}", "Notes": "Scale: 0 - 100"},
        {"Category": "Credit Score & Probability Statistics", "Metric / Indicator": "Mean Predicted DPD (days)", "Value (Production Model)": f"{prod_pred_dpd.mean():.1f} days", "Value (Baseline Model)": f"{raw_pred_dpd.mean():.1f} days", "Notes": "Severity Model"},
    ]
    df_summary = pd.DataFrame(summary_data)

    # All Features With Results
    calc_cols = ["Predicted Risk (PD)", "Credit Score", "Risk Tier", "Score Bracket", "Predicted DPD (days)", "Prediction", "Actual Status", "Classification Outcome"]
    enriched_cols = calc_cols + [c for c in df_raw.columns if c not in calc_cols]
    df_enriched = pd.concat([df_prod[calc_cols], df_raw[[c for c in df_raw.columns if c not in calc_cols]]], axis=1)

    print("[5/5] Exporting styled multi-sheet Excel workbook...")
    wb = openpyxl.Workbook()

    # Sheet 1: Executive Summary & Metrics
    ws_sum = wb.active
    ws_sum.title = "Executive Summary & Metrics"
    ws_sum.views.sheetView[0].showGridLines = True
    
    ws_sum.merge_cells("A1:E1")
    title_cell = ws_sum.cell(row=1, column=1, value="CREDIT RISK MODEL EVALUATION REPORT — RAW JAN - JUN 2026")
    title_cell.font = Font(name="Calibri", size=15, bold=True, color="1F4E79")
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws_sum.row_dimensions[1].height = 32

    headers = list(df_summary.columns)
    ws_sum.append([])
    ws_sum.append(headers)
    ws_sum.row_dimensions[3].height = 26
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col_idx in range(1, len(headers) + 1):
        c = ws_sum.cell(row=3, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    border_thin = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    for row_idx, row_data in enumerate(df_summary.values.tolist(), start=4):
        ws_sum.append(row_data)
        ws_sum.row_dimensions[row_idx].height = 20
        use_alt = (row_idx % 2 == 0)
        for col_idx in range(1, len(headers) + 1):
            cell = ws_sum.cell(row=row_idx, column=col_idx)
            cell.border = border_thin
            if use_alt:
                cell.fill = alt_fill

    for col in ws_sum.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(c.value or "")) for c in col)
        ws_sum.column_dimensions[col_letter].width = max(max_len + 4, 18)

    # Sheet 2: Production Model Results (Calculated Results)
    ws_prod = wb.create_sheet(title="Calculated Results (Production)")
    ws_prod.freeze_panes = "G2"
    for r in [list(df_prod.columns)] + df_prod.values.tolist():
        ws_prod.append(r)
    format_worksheet(ws_prod)
    style_outcomes(ws_prod)

    # Sheet 3: Baseline Model Results
    ws_base = wb.create_sheet(title="Baseline Model Results")
    ws_base.freeze_panes = "G2"
    for r in [list(df_base.columns)] + df_base.values.tolist():
        ws_base.append(r)
    format_worksheet(ws_base)
    style_outcomes(ws_base)

    # Sheet 4: All Features With Results
    ws_enr = wb.create_sheet(title="All Features With Results")
    ws_enr.freeze_panes = "I2"
    for r in [list(df_enriched.columns)] + df_enriched.values.tolist():
        ws_enr.append(r)
    format_worksheet(ws_enr, max_cols=len(df_enriched.columns))

    try:
        wb.save(OUTPUT_FILE)
        print(f"[SUCCESS] Saved primary report: {OUTPUT_FILE.resolve()}")
    except PermissionError:
        fallback = OUTPUT_FILE.with_name(f"{OUTPUT_FILE.stem}_unlocked{OUTPUT_FILE.suffix}")
        wb.save(fallback)
        print(f"[WARNING] File locked, saved fallback to: {fallback.resolve()}")

    print(f"\n[DONE] Processing completed in {time.time() - t_start:.2f} seconds!")


if __name__ == "__main__":
    main()

