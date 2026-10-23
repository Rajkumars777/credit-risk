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
import joblib

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.backend.ai_model import AIModel, resource_path


def load_model_bundle(model_dir: Path):
    """Load cached LightGBM model bundle."""
    model_files = list(model_dir.glob("*.joblib"))
    if not model_files:
        raise FileNotFoundError(f"No .joblib model bundle found in {model_dir}")
    bundle_path = model_files[0]
    print(f"[INFO] Loading trained model from: {bundle_path.name}")
    return joblib.load(bundle_path)


def assign_risk_tier(score: float) -> str:
    """Classify borrower risk tier based on credit score."""
    if score < 30.0:
        return "High Risk"
    elif score < 70.0:
        return "Moderate Risk"
    else:
        return "Low Risk"


def encode_dataset(df_processed: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    """Vectorized feature transformation matching AIModel inference."""
    features = bundle["features"]
    base_features = bundle.get("base_features", features)
    target_maps = bundle.get("target_maps", {})
    category_maps = bundle.get("category_maps", {})
    global_mean = bundle.get("global_mean", 0.15)
    medians = pd.Series(bundle.get("medians", {})).reindex(features).fillna(0.0)
    imputer = bundle.get("imputer")
    split_thresholds = bundle.get("split_thresholds", {})
    dropped_columns = bundle.get("dropped_columns", [])
    dealer_smooth = bundle.get("dealer_smooth", {})
    dealer_high_cutoff = bundle.get("dealer_high_cutoff", 0.0)
    dealer_mid_cutoff = bundle.get("dealer_mid_cutoff", 0.0)
    dealer_dti_cutoff = bundle.get("dealer_dti_cutoff", 0.0)

    frame = df_processed.drop(columns=["Longest_DPD", "Target"], errors="ignore").copy()

    dealer = "Dealer Name"
    if dealer in frame and dealer_smooth:
        rate = frame[dealer].astype(str).map(dealer_smooth).fillna(global_mean)
        tier = pd.cut(rate, [-np.inf, dealer_mid_cutoff, dealer_high_cutoff], labels=[0, 1]).astype(float).fillna(2)
        frame["Dealer_Default_Rate"] = rate
        frame["LoanHistory_x_DealerRisk"] = frame["Loan_History_Risk"] * rate
        frame["Dealer_x_LowDP"] = rate * (1 - frame["Downpayment"] / 100)
        frame["Dealer_x_Term"] = rate * frame["Payment Terms"]
        frame["Dealer_Risk_Tier"] = tier
        frame["High_Risk_Dealer"] = (tier == 2).astype(int)
        frame["Mid_Risk_Dealer"] = (tier == 1).astype(int)
        frame["GoodBorrower_RiskyDealer"] = ((tier >= 1) & (frame["DTI"] < dealer_dti_cutoff)).astype(int)
        frame["HighRiskMOP_x_DealerTier"] = frame["High_Risk_MOP"] * tier

    for column, mapping in target_maps.items():
        if column in frame:
            frame[f"{column}_TE"] = frame[column].astype(str).map(mapping).fillna(global_mean)

    frame = frame.drop(columns=[c for c in dropped_columns if c in frame], errors="ignore")

    for column, mapping in category_maps.items():
        if column in frame:
            frame[column] = frame[column].fillna("Unknown").astype(str).map(mapping).fillna(-1)

    frame = frame.reindex(columns=base_features, fill_value=np.nan)

    if imputer is not None:
        impute_columns = [c for c in ("Claimed Income", "Claimed Tenure", "DSCR", "Residence Tenure") if c in frame]
        if impute_columns:
            frame[impute_columns] = imputer.transform(frame[impute_columns])

    for column, threshold in split_thresholds.items():
        split_column = f"{column}_cd_split"
        if column in frame and split_column in features:
            frame[split_column] = (frame[column] <= threshold).astype(int)

    frame = frame.reindex(columns=features, fill_value=np.nan)
    return frame.apply(pd.to_numeric, errors="coerce").fillna(medians)


def run_testing(input_file: Path, output_file: Path = None, show_samples: int = 20):
    model_dir = PROJECT_ROOT / "src" / "backend" / "models"
    bundle = load_model_bundle(model_dir)
    model = bundle["model"]

    print(f"[INFO] Reading input data from: {input_file}")
    if input_file.suffix.lower() in [".xlsx", ".xls"]:
        df_raw = pd.read_excel(input_file)
    else:
        df_raw = pd.read_csv(input_file)

    print(f"[INFO] Loaded {len(df_raw):,} records. Preprocessing features...")
    df_aligned = df_raw.rename(columns={"Unit Brand": "Manufacturer"})
    df_processed = AIModel.process_data(df_aligned)

    # Encode features
    X_enc = encode_dataset(df_processed, bundle)

    print("[INFO] Computing model predictions and credit scores...")
    predicted_risk = model.predict_proba(X_enc)[:, 1]
    credit_scores = (1.0 - predicted_risk) * 100.0

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

