"""
Generate Dedicated Clean Result Workbook for Raw Jan - Jun 2026.xlsx
Preserves 100% of all 48 original raw data columns + appends pure model results.
No comparison sheets, no extra baseline noise — just pure 2026 results.
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sklearn.metrics import confusion_matrix, roc_auc_score, precision_score, recall_score, f1_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.backend.ai_model import AIModel
from src.frontend.main import App

INPUT_FILE = PROJECT_ROOT / "src/data/Raw Jan - Jun 2026.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "outputs/Raw_Jan_Jun_2026_Result.xlsx"


def assign_risk_tier(prob: float, threshold: float = 0.42) -> str:
    if prob >= threshold:
        return "High Risk"
    elif prob >= 0.20:
        return "Moderate Risk"
    else:
        return "Low Risk"


def assign_score_bracket(score: float) -> str:
    if score >= 70.0:
        return "Low Risk (70-100)"
    elif score >= 30.0:
        return "Moderate Risk (30-69)"
    else:
        return "High Risk (0-29)"


def main():
    print(f"[1/4] Loading {INPUT_FILE.name}...")
    df_raw = pd.read_excel(INPUT_FILE)
    print(f"      Loaded {len(df_raw):,} records with {len(df_raw.columns)} original columns.")

    print("[2/4] Initializing Production Model and running inference...")
    model = AIModel("src/data/May 12 Status Contracts.xlsx", "src/data/Extracted New.xlsx")
    ui = App.__new__(App)

    feature_rows = [
        ui._row_to_ai_features(ui._normalize_input_row(row))
        for row in df_raw.to_dict(orient="records")
    ]
    probabilities = model.predict_from_features_batch(feature_rows)
    predicted_dpds = model.predict_dpd_batch(feature_rows, risk_probs=probabilities)
    threshold = model.decision_threshold  # 0.42

    print(f"      Active Threshold: {threshold}")

    print("[3/4] Constructing enriched results DataFrame with ALL original columns...")
    df_out = df_raw.copy()

    probs = np.round(probabilities, 4)
    scores = np.round((1.0 - probabilities) * 100.0, 2)
    predictions = (probabilities >= threshold).astype(int)

    actual_dpd = pd.to_numeric(df_raw.get("Current DPD", np.nan), errors="coerce")
    actual_status = []
    classification = []
    for adpd, pred in zip(actual_dpd, predictions):
        if pd.isna(adpd):
            actual_status.append("Non-Default (Current / 0 DPD)")
            classification.append("False Positive (FP)" if pred == 1 else "True Negative (TN)")
        elif adpd > 10.0:
            actual_status.append("Default (DPD > 10)")
            classification.append("True Positive (TP)" if pred == 1 else "False Negative (FN)")
        else:
            actual_status.append("Non-Default (DPD <= 10)")
            classification.append("False Positive (FP)" if pred == 1 else "True Negative (TN)")

    # Model Result Columns
    df_out["Predicted Risk (PD)"] = probs
    df_out["Credit Score"] = scores
    df_out["Risk Tier"] = [assign_risk_tier(p, threshold) for p in probabilities]
    df_out["Score Bracket"] = [assign_score_bracket(s) for s in scores]
    df_out["Predicted DPD (days)"] = np.round(predicted_dpds, 1)
    df_out["Prediction"] = predictions
    df_out["Actual Status"] = actual_status
    df_out["Classification Outcome"] = classification

    # Ground truth metrics
    y_true = (actual_dpd.fillna(0) > 10.0).astype(int).to_numpy()
    tn, fp, fn, tp = confusion_matrix(y_true, predictions).ravel()
    rec = recall_score(y_true, predictions)
    spec = tn / (tn + fp)
    prec = precision_score(y_true, predictions)
    f1 = f1_score(y_true, predictions)
    auc = roc_auc_score(y_true, probabilities)

    print(f"\n      Ground Truth Evaluation:")
    print(f"      TN = {tn:,} | FP = {fp:,}")
    print(f"      FN = {fn:,} | TP = {tp:,}")
    print(f"      Recall: {rec*100:.2f}% | Specificity: {spec*100:.2f}% | AUC: {auc:.4f}")

    print("\n[4/4] Writing styled Excel workbook...")
    wb = openpyxl.Workbook()

    # Sheet 1: Results
    ws_results = wb.active
    ws_results.title = "Raw 2026 Results"
    ws_results.views.sheetView[0].showGridLines = True

    # Write headers
    headers = list(df_out.columns)
    ws_results.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    result_col_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")

    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    border_thin = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    fill_tp = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
    fill_tn = PatternFill(start_color="CFE2F3", end_color="CFE2F3", fill_type="solid")
    fill_fp = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")
    fill_fn = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")

    result_cols = {
        "Predicted Risk (PD)", "Credit Score", "Risk Tier", "Score Bracket",
        "Predicted DPD (days)", "Prediction", "Actual Status", "Classification Outcome"
    }

    ws_results.row_dimensions[1].height = 28
    for col_idx, h in enumerate(headers, 1):
        cell = ws_results.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = result_col_fill if h in result_cols else header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    outcome_col_idx = headers.index("Classification Outcome") + 1

    # Write rows
    for r_idx, row_vals in enumerate(df_out.itertuples(index=False), 2):
        ws_results.append(list(row_vals))
        ws_results.row_dimensions[r_idx].height = 20
        use_alt = (r_idx % 2 == 0)

        for c_idx in range(1, len(headers) + 1):
            cell = ws_results.cell(row=r_idx, column=c_idx)
            cell.border = border_thin
            if use_alt and cell.fill.fill_type is None:
                cell.fill = alt_fill

        # Color the Classification Outcome
        out_cell = ws_results.cell(row=r_idx, column=outcome_col_idx)
        v = str(out_cell.value or "")
        if "True Positive" in v:
            out_cell.fill = fill_tp
        elif "True Negative" in v:
            out_cell.fill = fill_tn
        elif "False Positive" in v:
            out_cell.fill = fill_fp
        elif "False Negative" in v:
            out_cell.fill = fill_fn

    for col in range(1, len(headers) + 1):
        col_letter = get_column_letter(col)
        h_name = headers[col - 1]
        ws_results.column_dimensions[col_letter].width = max(len(h_name) + 4, 12)

    # Sheet 2: Confusion Matrix & Metrics
    ws_matrix = wb.create_sheet(title="Confusion Matrix")
    ws_matrix.views.sheetView[0].showGridLines = True

    title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    ws_matrix["A1"] = "CONFUSION MATRIX — RAW JAN - JUN 2026 (Threshold = 0.42)"
    ws_matrix["A1"].font = title_font

    # 2x2 Matrix Table
    matrix_headers = ["Actual \\ Predicted", "Predicted Performing (Score < 0.42)", "Predicted Default (Score >= 0.42)", "Total Actual"]
    for col_idx, text in enumerate(matrix_headers, 1):
        cell = ws_matrix.cell(row=3, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
    ws_matrix.row_dimensions[3].height = 26

    matrix_rows = [
        ("Actual Performing (DPD <= 10)", tn, fp, tn + fp),
        ("Actual Default (DPD > 10)", fn, tp, fn + tp),
        ("Total Predicted", tn + fn, fp + tp, tn + fp + fn + tp),
    ]

    for r_idx, (label, c1, c2, tot) in enumerate(matrix_rows, 4):
        ws_matrix.row_dimensions[r_idx].height = 22
        cell_lbl = ws_matrix.cell(row=r_idx, column=1, value=label)
        cell_lbl.font = bold_font

        cell_c1 = ws_matrix.cell(row=r_idx, column=2, value=c1)
        cell_c1.font = regular_font if r_idx != 6 else bold_font
        cell_c1.alignment = center_align
        cell_c1.number_format = "#,##0"

        cell_c2 = ws_matrix.cell(row=r_idx, column=3, value=c2)
        cell_c2.font = regular_font if r_idx != 6 else bold_font
        cell_c2.alignment = center_align
        cell_c2.number_format = "#,##0"

        cell_tot = ws_matrix.cell(row=r_idx, column=4, value=tot)
        cell_tot.font = bold_font
        cell_tot.alignment = center_align
        cell_tot.number_format = "#,##0"

    # Color matrix cells
    ws_matrix.cell(row=4, column=2).fill = fill_tn
    ws_matrix.cell(row=4, column=3).fill = fill_fp
    ws_matrix.cell(row=5, column=2).fill = fill_fn
    ws_matrix.cell(row=5, column=3).fill = fill_tp

    for r in range(3, 7):
        for c in range(1, 5):
            ws_matrix.cell(row=r, column=c).border = border_thin

    # Metrics Summary Table
    ws_matrix["A9"] = "PERFORMANCE METRICS"
    ws_matrix["A9"].font = Font(name="Calibri", size=12, bold=True, color="1F4E79")

    metrics_data = [
        ("Default Recall (Sensitivity)", f"{rec*100:.2f}%"),
        ("Specificity (Performing Approved)", f"{spec*100:.2f}%"),
        ("Precision", f"{prec*100:.2f}%"),
        ("F1-Score", f"{f1:.4f}"),
        ("ROC-AUC", f"{auc:.4f}"),
        ("Decision Threshold", f"{threshold:.2f}"),
        ("Total Portfolio Records", f"{len(df_raw):,}"),
    ]

    ws_matrix.cell(row=10, column=1, value="Metric").font = header_font
    ws_matrix.cell(row=10, column=1).fill = header_fill
    ws_matrix.cell(row=10, column=2, value="Value").font = header_font
    ws_matrix.cell(row=10, column=2).fill = header_fill
    ws_matrix.row_dimensions[10].height = 24

    for r_idx, (m_label, m_val) in enumerate(metrics_data, 11):
        ws_matrix.row_dimensions[r_idx].height = 20
        c1 = ws_matrix.cell(row=r_idx, column=1, value=m_label)
        c2 = ws_matrix.cell(row=r_idx, column=2, value=m_val)
        c1.font = regular_font
        c2.font = bold_font
        c2.alignment = center_align
        c1.border = border_thin
        c2.border = border_thin

    ws_matrix.column_dimensions["A"].width = 38
    ws_matrix.column_dimensions["B"].width = 36
    ws_matrix.column_dimensions["C"].width = 36
    ws_matrix.column_dimensions["D"].width = 18

    # Save cleanly
    try:
        wb.save(OUTPUT_FILE)
        print(f"\n[SUCCESS] Successfully saved dedicated result workbook:")
        print(f"          {OUTPUT_FILE}")
    except PermissionError:
        fallback = OUTPUT_FILE.with_name(f"{OUTPUT_FILE.stem}_unlocked{OUTPUT_FILE.suffix}")
        wb.save(fallback)
        print(f"\n[LOCKED] File is open in Excel. Saved to fallback:")
        print(f"         {fallback}")


if __name__ == "__main__":
    main()

