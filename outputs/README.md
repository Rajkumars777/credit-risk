# Model Evaluation & Comparison Outputs

This directory contains generated Excel workbooks and reports produced by the evaluation scripts in `scripts/`.

---

## 📊 Summary of Workbooks

| File | Description | Generating Script |
| :--- | :--- | :--- |
| `Model_Comparison_Raw_vs_Production.xlsx` | Side-by-side performance comparison of Initial Raw Model vs. Production Optimization Model across all metrics (Confusion Matrix, Precision, Recall, F1, ROC-AUC) | `scripts/generate_comparison_excels.py` |
| `Production_Optimization_Model_Result.xlsx` | Granular prediction results from the calibrated Production Optimization Model evaluated on 2026 contracts | `scripts/generate_comparison_excels.py` |
| `Initial_Raw_Model_Result.xlsx` | Baseline predictions from the uncalibrated historical LightGBM model | `scripts/generate_comparison_excels.py` |
| `Raw_Jan_Jun_2026_Result.xlsx` | Comprehensive multi-tab evaluation report on `Raw Jan - Jun 2026.xlsx` (2,845 records) including summary KPIs and detailed contract scoring | `scripts/generate_raw_2026_results.py` |
| `May_12_Status_Contracts_Result.xlsx` | Full portfolio evaluation report on `May 12 Status Contracts.xlsx` (22,300 records) | `scripts/generate_may_12_results.py` |

---

## 🔄 Re-generating Outputs

To re-generate any of these reports, run the corresponding script:

```powershell
# Comparison workbooks
python scripts/generate_comparison_excels.py

# 2026 contracts evaluation
python scripts/generate_raw_2026_results.py

# May 12 portfolio evaluation
python scripts/generate_may_12_results.py
```

