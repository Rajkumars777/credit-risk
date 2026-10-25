"""
Credit Scoring Model Evaluation & Testing Script
Produces predictions with:
  Contract ID | App No | Amount Financed | Predicted Risk | Credit Score | Risk Tier
And displays score bracket counts:
  [0 to 29], [30 to 69], [70 to 100]
"""

import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.backend.ai_model import AIModel
from src.frontend.main import App


def assign_risk_tier(score: float) -> str:
    """Classify borrower risk tier based on credit score."""
    if score < 30.0:
        return "High Risk"
    elif score < 70.0:
        return "Moderate Risk"
    else:
        return "Low Risk"


def run_testing(input_file: Path, output_file: Path = None, show_samples: int = 20):
    model = AIModel("src/data/May 12 Status Contracts.xlsx", "src/data/Extracted New.xlsx")
    ui_input = App.__new__(App)

    print(f"[INFO] Reading input data from: {input_file}")
    if input_file.suffix.lower() in [".xlsx", ".xls"]:
        df_raw = pd.read_excel(input_file)
    else:
        df_raw = pd.read_csv(input_file)

    print(f"[INFO] Loaded {len(df_raw):,} records. Preprocessing features...")
    print("[INFO] Computing model predictions and credit scores using the UI inference path...")
    ui_rows = []
    for row in df_raw.to_dict(orient="records"):
        normalized = ui_input._normalize_input_row(row)
        ui_rows.append(ui_input._row_to_ai_features(normalized))
    predicted_risk = model.predict_from_features_batch(ui_rows)

    credit_scores = (1.0 - predicted_risk) * 100.0
    df_processed = df_raw.rename(columns={"Current DPD": "Longest_DPD"})

    # Build results DataFrame with exact columns requested
    contract_id = df_processed.get("Contract ID", df_raw.get("Contract ID", pd.Series(range(1, len(df_processed) + 1))))
    app_no = df_processed.get("Application No", df_raw.get("Application No", pd.Series(range(1, len(df_processed) + 1))))
    amount_financed = df_processed.get("Amount Finance", df_raw.get("Amount Finance", pd.Series(np.nan, index=df_processed.index)))

    results_df = pd.DataFrame({
        "Contract ID": contract_id.values,
        "App No": app_no.values,
        "Amount Financed": amount_financed.values,
        "Predicted Risk": np.round(predicted_risk, 4),
        "Credit Score": np.round(credit_scores, 2),
    })
    results_df["Risk Tier"] = results_df["Credit Score"].apply(assign_risk_tier)

    # If ground truth DPD is available, optionally include for validation
    if "Longest_DPD" in df_processed:
        results_df["Actual DPD"] = df_processed["Longest_DPD"].values

    # Preview sample records
    print("\n" + "=" * 90)
    print(f"SAMPLE TEST RESULTS (Showing {min(show_samples, len(results_df))} of {len(results_df):,} records)")
    print("=" * 90)
    header = f"{'Contract ID':<15} {'App No':<12} {'Amount Financed':>15} {'Predicted Risk':>16} {'Credit Score':>14} {'Risk Tier':<15}"
    print(header)
    print("-" * 90)

    # Take stratified sample across tiers for representative preview
    preview_rows = []
    for tier in ["High Risk", "Moderate Risk", "Low Risk"]:
        tier_sub = results_df[results_df["Risk Tier"] == tier]
        if not tier_sub.empty:
            preview_rows.append(tier_sub.head(max(2, show_samples // 3)))
    if preview_rows:
        preview_df = pd.concat(preview_rows).head(show_samples)
    else:
        preview_df = results_df.head(show_samples)

    for _, r in preview_df.iterrows():
        cid = str(r["Contract ID"])
        app = str(r["App No"])
        amt = f"{r['Amount Financed']:,.2f}" if pd.notna(r["Amount Financed"]) else "N/A"
        risk = f"{r['Predicted Risk']:.4f} ({r['Predicted Risk']*100:.1f}%)"
        sc = f"{r['Credit Score']:.2f}"
        tier = r["Risk Tier"]
        print(f"{cid:<15} {app:<12} {amt:>15} {risk:>16} {sc:>14} {tier:<15}")

    # Summary count by requested bins
    total_records = len(results_df)
    count_0_29 = int((results_df["Credit Score"] < 30.0).sum())
    count_30_69 = int(((results_df["Credit Score"] >= 30.0) & (results_df["Credit Score"] < 70.0)).sum())
    count_70_100 = int((results_df["Credit Score"] >= 70.0).sum())

    pct_0_29 = (count_0_29 / total_records) * 100.0 if total_records > 0 else 0.0
    pct_30_69 = (count_30_69 / total_records) * 100.0 if total_records > 0 else 0.0
    pct_70_100 = (count_70_100 / total_records) * 100.0 if total_records > 0 else 0.0

    print("\n" + "=" * 90)
    print("TEST RESULTS SUMMARY - CREDIT SCORE BRACKET COUNTS")
    print("=" * 90)
    print(f"Total Records Tested: {total_records:,}")
    print("-" * 90)
    print(f"  Score   0 to 29  (High Risk)     : {count_0_29:7,d} records  ({pct_0_29:5.2f}%)")
    print(f"  Score  30 to 69  (Moderate Risk) : {count_30_69:7,d} records  ({pct_30_69:5.2f}%)")
    print(f"  Score  70 to 100 (Low Risk)      : {count_70_100:7,d} records  ({pct_70_100:5.2f}%)")
    print("=" * 90)

    # Save to CSV if path provided or default
    if output_file:
        output_file = Path(output_file)
        results_df.to_csv(output_file, index=False)
        print(f"\n[INFO] Full results ({len(results_df):,} rows) exported to: {output_file.resolve()}\n")

    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test credit scoring model on dataset")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "src" / "data" / "Extracted New.xlsx"),
        help="Path to input Excel or CSV file (default: src/data/Extracted New.xlsx)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "test_results.csv"),
        help="Path to save output CSV (default: test_results.csv)",
    )
    parser.add_argument(
        "--samples",
        "-s",
        type=int,
        default=15,
        help="Number of preview records to display (default: 15)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        print(f"[ERROR] Input file does not exist: {input_path}")
        sys.exit(1)

    run_testing(input_path, output_path, show_samples=args.samples)
