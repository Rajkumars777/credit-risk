# JACCS Credit Scoring System

A desktop credit-scoring application built with Python and Tkinter.

## Project Overview

This project provides a credit scoring workflow for JACCS-style loan evaluation, including:

- User authentication
- Admin dashboard access
- Credit scoring workflow
- AI model loading and scoring
- Local SQLite-backed data handling

## Project Structure

```text
credit-scoring-app/
├── src/
│   ├── backend/
│   │   ├── ai_model.py
│   │   ├── db.py
│   │   ├── users.py
│   │   ├── models/
│   │   └── database/
│   ├── frontend/
│   │   ├── main.py
│   │   ├── splash.py
│   │   └── admin_dashboard.py
│   └── data/
│       ├── img/
│       ├── Extracted New.xlsx
│       └── May 12 Status Contracts.xlsx
├── users.csv
├── README.md
├── ltid_logo(1).ico
├── .venv/
└── output/
```

## Requirements

Use the project virtual environment and install dependencies from the project requirements file:

```powershell
cd D:\LTID\credit-scoring-app
.\.venv\Scripts\Activate.ps1
pip install -r src\requirements.txt
```

## Run the app

```powershell
cd D:\LTID\credit-scoring-app
.\.venv\Scripts\Activate.ps1
python src\frontend\main.py
```

Before using database-backed features, configure the connection with
`save_config()` or by editing `src\backend\data\database\db_config.json`.
Credentials are intentionally not stored in this repository.

## Validate later-period performance

Evaluate predictions against rows with observed `Current DPD` in the later
January–June 2026 dataset. A default is defined as `Current DPD > 1`; rows
without an observed DPD are excluded. The evaluator reports precision, recall,
F1-score, ROC-AUC, average precision, and the confusion matrix:

```powershell
python .\tests\evaluate_later_performance.py
```

The evaluator uses only customer application features for prediction and uses
`Current DPD` only as the ground-truth label. Because the current later-period
file contains very few non-default labels, interpret precision/recall and
ROC-AUC together with the reported class counts. The model's decision
threshold is selected on its validation split using recall-weighted F2-score,
with a minimum precision guard; ROC-AUC continues to use the raw probabilities.

## Build executable with PyInstaller

Use the following command from the project root:

```powershell
pyinstaller --noconfirm --onefile --windowed --icon "D:\LTID\credit-scoring-app\ltid_logo(1).ico" --name "JACCSScore" --add-data "D:\LTID\credit-scoring-app\src;src/" --add-data "D:\LTID\credit-scoring-app\src\data\img;img" --add-data "D:\LTID\credit-scoring-app\src\backend\models\May 12 Status Contracts_Extracted New_lgbm.joblib;src/backend/models/" "D:\LTID\credit-scoring-app\src\frontend\main.py"
```

## Notes

- The app expects project resources under the `src` folder and bundled image assets under `img` during packaged execution.
- If the model file path changes, update the `--add-data` entry accordingly.
- The built executable will be created inside the `dist` folder by default.

## Troubleshooting

If the packaged app fails to launch:

1. Confirm that all required data files still exist in the project.
2. Confirm that the model file path in the PyInstaller command matches the actual file name.
3. Confirm that the app is resolving files using the correct resource paths in the code.
4. Rebuild after verifying the project structure.

## License

This project is for internal/local use and should be used according to your organization’s requirements.
