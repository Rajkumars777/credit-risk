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
