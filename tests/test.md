Ran check tests directory
Analyzed test_csv_preprocessing.py:L1-19
Created test_model_predictions.py
Ran execute test script on Extracted New.xlsx
Timed 20s
Checked task Execute test script on Extracted New.xlsx
Analyzed task-267.log
Checked task Execute test script on Extracted New.xlsx
Timed 20s
Checked task Execute test script on Extracted New.xlsx
Analyzed task-267.log:L1
Checked task Execute test script on Extracted New.xlsx
Timed 15s
Checked task Execute test script on Extracted New.xlsx
Checked task Execute test script on Extracted New.xlsx

A test script has been created at [`tests/test_model_predictions.py`](file:///c:/Users/rajak/Videos/ltid-oct/credit-scoring-app/tests/test_model_predictions.py) to evaluate any dataset and produce individual contract predictions alongside the requested risk-bracket counts.

---

### 1. Test Results on `Extracted New.xlsx`

```text
==========================================================================================
SAMPLE TEST RESULTS (Showing representative records across tiers)
==========================================================================================
Contract ID     App No       Amount Financed   Predicted Risk   Credit Score Risk Tier      
------------------------------------------------------------------------------------------
30425           1.0               402,500.00   0.9162 (91.6%)           8.38 High Risk      
30452           2.0               980,000.00   0.9120 (91.2%)           8.80 High Risk      
30642           1.0               585,000.00   0.9150 (91.5%)           8.50 High Risk      
30676           1.0               455,000.00   0.9150 (91.5%)           8.50 High Risk      
30903           1.0               330,000.00   0.8944 (89.4%)          10.56 High Risk      
30447           1.0               567,000.00   0.6206 (62.1%)          37.94 Moderate Risk  
31977           1.0               480,000.00   0.6708 (67.1%)          32.92 Moderate Risk  
32161           1.0               585,000.00   0.5610 (56.1%)          43.90 Moderate Risk  
32540           1.0               682,500.00   0.6544 (65.4%)          34.56 Moderate Risk  
32908           1.0               348,600.00   0.6511 (65.1%)          34.89 Moderate Risk  
30373           1.0               451,500.00   0.0289  (2.9%)          97.11 Low Risk       
30374           1.0               455,000.00   0.0365  (3.6%)          96.35 Low Risk       
30380           1.0               537,550.00   0.0021  (0.2%)          99.79 Low Risk       
30380           2.0               537,550.00   0.0030  (0.3%)          99.70 Low Risk       
30382           1.0               660,000.00   0.0309  (3.1%)          96.91 Low Risk       
```

---

### 2. Credit Score Bracket Counts

```text
==========================================================================================
TEST RESULTS SUMMARY - CREDIT SCORE BRACKET COUNTS
==========================================================================================
Total Records Tested: 25,672
------------------------------------------------------------------------------------------
  Score   0 to 29  (High Risk)     :    3,077 records  (11.99%)
  Score  30 to 69  (Moderate Risk) :      597 records  ( 2.33%)
  Score  70 to 100 (Low Risk)      :   21,998 records  (85.69%)
==========================================================================================
```

The full dataset output with all 25,672 individual rows has been exported to:
[`tests/extracted_new_results.csv`](file:///c:/Users/rajak/Videos/ltid-oct/credit-scoring-app/tests/extracted_new_results.csv).

---

### 3. How to Run the Script

You can re-run the test script anytime from your terminal:

```powershell
# Run with default input (Extracted New.xlsx)
python tests/test_model_predictions.py

# Or specify custom input, output CSV path, and sample count:
python tests/test_model_predictions.py --input "src/data/Extracted New.xlsx" --output "test_results.csv" --samples 20
```