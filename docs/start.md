# JACCS Credit Scoring App - Setup and Run Guide

This guide explains how to set up and run the credit-scoring application on
Windows using PowerShell.

## 1. Clone the repository

Open PowerShell and run:

```powershell
git clone https://github.com/LTID-rep/credit-scoring-app.git
cd credit-scoring-app
```

If the repository is already cloned, go directly to the project folder:

```powershell
cd C:\path\to\credit-scoring-app
```

## 2. Check Python

The application requires Python 3.13 or a compatible Python 3 version.
Confirm that Python is available:

```powershell
python --version
```

## 3. Create a virtual environment

Run this from the project root:

```powershell
python -m venv .venv
```

## 4. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, allow scripts for the current user and
activate the environment again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

When the environment is active, `(.venv)` appears at the beginning of the
PowerShell prompt.

## 5. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
```

## 6. Run the application

Run the application from the project root:

```powershell
python .\src\frontend\main.py
```

Keep the terminal open while the application is running.

## 7. Run the model prediction test

To test the trained model with the sample CSV file:

```powershell
python .\tests\test_model_predictions.py `
  --input .\test_data\sample_data.csv `
  --output .\test_results.csv `
  --samples 15
```

The results are written to `test_results.csv` in the project root.

## 8. Deactivate the virtual environment

When finished, run:

```powershell
deactivate
```

## Troubleshooting

### `ModuleNotFoundError`

Make sure the virtual environment is active and install the dependencies
again:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
```

### The model cannot be found

Run the commands from the project root and confirm that this file exists:

```text
src\backend\models\May 12 Status Contracts_Extracted New_lgbm.joblib
```

### The input file cannot be found

Use an absolute path or confirm that the input path is relative to the project
root. For example:

```powershell
Test-Path .\test_data\sample_data.csv
```
