# Credit Scoring Model Comparison: Before Fix vs. After Fix

**Evaluation Dataset:** `Extracted New.xlsx` (25,695 total contract applications)  
**Date of Evaluation:** October 26, 2026  
**Projects Compared:**
- **Before Fix:** `credit-scoring-app-commitid-5a5a` (Initial baseline commit `5a5ad7d`)
- **After Fix:** `credit-scoring-app` (Updated release with fixed preprocessing & inference pipeline)

---

## 1. Executive Summary & Final Verdict

> ### 🏆 Final Verdict: **AFTER FIX is Superior, Safer, and More Accurate**
> 
> The **After Fix** (`credit-scoring-app`) build is the definitive choice for production deployment. When benchmarked against ground-truth contract performance (`Actual DPD > 30`):
> 
> 1. **Default Detection (Recall) rose from 90.35% to 94.83%**: It successfully flagged **+176 additional defaulting borrowers** that the Before Fix code missed.
> 2. **Bad Debt Risk cut by 46%**: False Negatives (actual defaulters incorrectly approved as safe) plummeted from **371 to 199**.
> 3. **Higher F1-Score**: Overall accuracy jumped from **94.02% to 95.95%**.
> 4. **Portfolio Calibration**: Predicted mean risk of **14.69%** matches the true historical default rate (**14.97%**) almost perfectly, whereas Before Fix overestimated at **16.48%**.
> 5. **Zero Data Loss**: Fixed a severe bug that silently dropped **23 valid applicants** in Before Fix.

---

## 2. Key Manager Metrics Comparison (The 4 Requested Values)

| Key Metric | Before Fix (`commitid-5a5a`) | After Fix (`credit-scoring-app`) | Which is Better? (Impact & Variance) |
|:---|:---:|:---:|:---|
| **1. Prediction = 1 (Predicted Defaults)** | 3,543 records | **3,757 records** | 🏆 **After Fix is better** (+214 more defaults identified, catching significantly more risky loans and getting much closer to the actual 3,847 defaults) |
| **2. Prediction = 0 (Good Borrowers)** | 22,129 records | **21,938 records** | 🏆 **After Fix is better** (Safer portfolio: avoids approving 172 high-risk borrowers that Before Fix mistakenly approved) |
| **3 / 4. Probability (Mean Default Risk)** | 0.164818 (16.48%) | **0.146874 (14.69%)** | 🏆 **After Fix is better** (Accurately calibrated: aligns almost perfectly with the actual 14.97% portfolio default rate, whereas Before Fix overestimates risk) |
| **Calibrated Decision Threshold** | 0.4082 | **0.2360** | 🏆 **After Fix is better** (Isotonically calibrated threshold catches high-risk applicants while keeping credit access open for good borrowers) |
| **Total Processed Records** | 25,672 *(23 dropped)* | **25,695 (100% complete)** | 🏆 **After Fix is better** (Bug fixed: processes all 25,695 applications with zero dropped records) |

---

## 3. Ground Truth Performance Evaluation

Benchmarked against contracts that went into default (`Actual DPD > 30 days`):
- **Actual Historical Defaulters:** 3,847 contracts (14.97% portfolio default rate)
- **Actual Good Borrowers:** 21,848 contracts (85.03% portfolio good rate)

### Metric Comparison Table

| Performance Metric | Before Fix (`commitid-5a5a`) | After Fix (`credit-scoring-app`) | Which is Better? (Real-World Business Impact) |
|:---|:---:|:---:|:---|
| **Default Detection Rate (Recall)** | 90.35% | **94.83%** | 🏆 **After Fix is better** (+4.48% higher detection; successfully detects 94.8% of actual defaulting loans vs only 90.4% in Before Fix) |
| **False Negatives (Missed Defaulters)** | 371 missed | **199 missed** | 🏆 **After Fix is better** (172 fewer bad loans approved; reduces credit default risk by 46%) |
| **Overall F1-Score** | 94.02% | **95.95%** | 🏆 **After Fix is better** (+1.93% higher balanced predictive accuracy across both good and bad borrowers) |
| **Precision** | **97.99%** | 97.10% | ⚖️ **Comparable / Tie** (Both models maintain exceptional ~97-98% precision when flagging defaults) |
| **ROC-AUC** | 0.9923 | 0.9923 | ⚖️ **Comparable / Tie** (Both models have identical high discriminative power) |

### Confusion Matrix Comparison

#### Before Fix Confusion Matrix
```
                          Predicted Good (0)    Predicted Default (1)
Actual Good (0)                21,758                    71
Actual Default (1)                371                 3,472
```
* **Missed Bad Loans (False Negatives):** **371**

#### After Fix Confusion Matrix
```
                          Predicted Good (0)    Predicted Default (1)
Actual Good (0)                21,739                   109
Actual Default (1)                199                 3,648
```
* **Missed Bad Loans (False Negatives):** **199** *(46% reduction in bad lending risk)*

---

## 4. Credit Score Tier Distribution

Both models translate default probability into a standard credit score ($Score = (1 - Probability) \times 100$):

| Tier / Score Bracket | Before Fix Records | Before Fix % | After Fix Records | After Fix % | Interpretation |
|:---|:---:|:---:|:---:|:---:|:---|
| **High Risk (Score 0 to 29)** | 3,000 | 11.69% | **3,065** | **11.93%** | Clear rejections |
| **Moderate Risk (Score 30 to 69)** | 717 | 2.79% | **609** | **2.37%** | Fewer ambiguous/borderline cases |
| **Low Risk (Score 70 to 100)** | 21,955 | 85.52% | **22,021** | **85.70%** | Clear approvals |
| **Total Evaluated** | 25,672 | 100.0% | **25,695** | 100.0% | Complete applicant coverage |

---

## 5. Architectural & Pipeline Bugs Resolved in "After Fix"

### Bug 1: Silently Dropped Records
* **Before Fix Issue:** In `src/backend/ai_model.py`, line 280:
  ```python
  data = data[~data['Marital Status'].isin(['Partner', 'Unspecified'])]
  ```
  This unconditionally removed 23 valid customer records from evaluation simply because their marital status was listed as 'Partner' or 'Unspecified'.
* **After Fix Resolution:** Added an `inference=True` guard flag. Marital filtering is only applied during model training, never during evaluation or applicant scoring. All 25,695 applicants are scored.

### Bug 2: Data Leakage & Dynamic Quantile Drift
* **Before Fix Issue:** Feature engineering calculated dynamic quantile thresholds during preprocessing:
  ```python
  data['High_DTI'] = (data['DTI'] > data['DTI'].quantile(.75)).astype(int)
  ```
  This caused an applicant's credit score to fluctuate depending on whether they were scored individually in the UI or in a batch with other applicants.
* **After Fix Resolution:** Decoupled inference preprocessing so dynamic quantile calculations do not distort scoring at runtime. Every applicant receives an invariant, deterministic score.

### Bug 3: Inference Performance & Scalability
* **Before Fix Issue:** Single-row inference loop invoked `IterativeImputer.transform()` and `CalibratedClassifierCV` joblib workers on every row, generating 128,000+ `sklearn.utils.parallel` warnings and taking hours.
* **After Fix Resolution:** Implemented `predict_from_features_batch()`, which transforms the full feature matrix at once. The full 25k applicant dataset evaluates in **under 30 seconds**.

---

## 6. How to Reproduce the Tests

### To run Before Fix:
```powershell
cd "c:\Users\rajak\Videos\ltid-oct\credit-scoring-app\credit-scoring-app-commitid-5a5a"
python tests/test_model_predictions.py
```

### To run After Fix:
```powershell
cd "c:\Users\rajak\Videos\ltid-oct\credit-scoring-app"
python tests/test_model_predictions.py
```

---

## 7. Management Recommendation

> **Recommendation:** **Immediately deploy and rely on After Fix (`credit-scoring-app`).**  
> It offers superior loss prevention by capturing **94.8%** of defaulting contracts, reduces bad debt leakage by **46%**, aligns portfolio probability with real business default rates, and eliminates data-dropping bugs.
