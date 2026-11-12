# Maintenance, Training, and Evaluation Scripts

This directory contains standalone CLI scripts for model training, portfolio evaluation, database management, and report generation.

---

## 🚀 Model Training & Calibration

- `train_and_save_production_model.py`: Trains the unified LightGBM model bundle combining the May 12 contracts portfolio with later 2026 data. Caches directly into `src/backend/models/`.

```powershell
python scripts/train_and_save_production_model.py
```

---

## 📈 Evaluation & Report Generation

- `generate_comparison_excels.py`: Produces side-by-side comparison workbooks between baseline and production models into `outputs/`.
- `generate_raw_2026_results.py`: Scores the 2,845 records from `src/data/Raw Jan - Jun 2026.xlsx` into `outputs/Raw_Jan_Jun_2026_Result.xlsx`.
- `generate_may_12_results.py`: Scores the 22,300 records from `src/data/May 12 Status Contracts.xlsx` into `outputs/May_12_Status_Contracts_Result.xlsx`.
- `evaluate_later_performance.py`: Evaluates predictions against observed DPD labels.
- `evaluate_all_models.py`: Historical model comparison benchmarks.

---

## 📑 Document Generators (`scripts/reports/`)

- `create_comparison_pdf.py`: Headless browser-rendered PDF comparison report.
- `generate_comparison_docx.py`: Generates `docs/reports/MODEL_COMPARISON_BEFORE_VS_AFTER_FIX.docx`.
- `generate_app_vs_colab_docx.py`: Generates `docs/reports/CREDIT_SCORING_APP_VS_COLAB_COMPARISON.docx`.

---

## 🗄️ Database (`scripts/sql/`)

- `schema.sql`: Microsoft SQL Server table definition and database creation script for customer and contract records.

