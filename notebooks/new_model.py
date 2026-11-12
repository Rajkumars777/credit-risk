# ai_model.py

import sys
import os
import hashlib
import re
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.model_selection import train_test_split
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.calibration import CalibratedClassifierCV
import joblib
import shap
import json, difflib
from lightgbm import LGBMClassifier


def resource_path(rel_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel_path)  # type: ignore[attr-defined]
    return os.path.join(os.path.dirname(__file__), rel_path)


def _excel_sha1(path: str) -> str:
    """Fast-ish SHA1 of a file to detect changes."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _model_path_for_excel(excel_filenames: tuple[str, ...]) -> str:
    """Where to store the cached model bundle."""
    base_dir = Path(os.path.dirname(__file__)) / "models"
    base_dir.mkdir(exist_ok=True)
    stem = "_".join(Path(filename).stem for filename in excel_filenames)
    return str(base_dir / f"{stem}_rf.joblib")


def _combined_excel_sha1(paths: List[str]) -> str:
    """Create one cache signature for all input workbooks."""
    digest = hashlib.sha1()
    for path in paths:
        digest.update(os.path.basename(path).encode("utf-8"))
        digest.update(_excel_sha1(path).encode("ascii"))
    return digest.hexdigest()


class AIModel:
    """
    Aug-19 Final pipeline with model caching.

    On __init__:
      - If a cached bundle exists and matches the Excel file's SHA1, load it.
      - Else, train from Excel and save the bundle for next startup.
    """

    TARGET = "Longest DPD"

    CATEGORICAL_COLS: List[str] = [
        "Asset",
        "Manufacturer",
        "Type of Unit",
        "Loan History",
        "BAP Type",
        "Employment Type",
        "Home Ownership",
        "Citizenship",
        "Dealer Name",
        "Submitted ID",
        "Product Type",
        "Mode of Payment",
        "Co-Borrowers",
        "Borrower Type",
        "Marital Status",
    ]

    HARISH_TE_COLS = [
        "Dealer Name", "Manufacturer", "Asset", "Employment Type",
        "Product Type", "Home Ownership", "Loan History", "BAP Type",
        "Mode of Payment",
    ]
    RAW_INPUT_FEATURES = [
        "Amount Finance", "Downpayment", "Downpayment %", "Payment Terms",
        "Asset", "Manufacturer", "Type of Unit", "Price Gap", "Loan History",
        "BAP Type", "BAP Amount", "Interest Rate", "Claimed Income",
        "EV Income", "BV Income", "Employment Type", "Claimed Tenure",
        "EV Tenure", "BV Tenure", "DSCR", "Age as of Contract",
        "Home Ownership", "Residence Tenure", "Citizenship", "Dealer Name",
        "Submitted ID", "Marital Status", "Loan Amort", "Product Type",
        "Mode of Payment", "Co-Borrowers", "Borrower Type", "Contract Start Date",
    ]
    HARISH_DROP_COLS = {
        "Citizenship", "Contract_Year", "Type of Unit", "Borrower Type",
        "Dealer_Default_Rate", "LoanHistory_x_DealerRisk", "Dealer_x_LowDP",
        "Dealer_x_Term", "High_Risk_Dealer", "Mid_Risk_Dealer",
        "Dealer_Risk_Tier", "GoodBorrower_RiskyDealer", "Submitted ID",
    }
    HARISH_BEST_PARAMS = {
        "n_estimators": 1386, "max_depth": 12, "num_leaves": 184,
        "min_child_samples": 6, "learning_rate": 0.1538862143578627,
        "subsample": 0.7517993141753957,
        "colsample_bytree": 0.6008938631093506,
        "reg_alpha": 0.00012940233398199124,
        "reg_lambda": 0.00022914020156036827,
        "scale_pos_weight": 19.120797456529292,
    }

    def __init__(self, *excel_filenames: str):
        # if len(excel_filenames) != 2:
        #     raise TypeError("AIModel requires exactly two Excel filenames.")

        # Resolve paths
        self.excel_paths = [resource_path(filename) for filename in excel_filenames]
        missing = [path for path in self.excel_paths if not os.path.exists(path)]
        if missing:
            raise FileNotFoundError("Training workbook(s) not found: " + ", ".join(missing))
        # self.excel_path = self.excel_paths[0] --> For ONE File Input handeling
        self.model_path = _model_path_for_excel(tuple(excel_filenames))
        self._loaded_from_cache = False

        # NEW: make sure these always exist
        self._loaded_from_cache = False
        self._ext_enc = None  # <— important
        self._explainer = None  # SHAP (lazy)

        # Try to load cached model first
        excel_sig = _combined_excel_sha1(self.excel_paths)
        if os.path.exists(self.model_path):
            try:
                bundle = joblib.load(self.model_path)
                if bundle.get("excel_sha1") == excel_sig and bundle.get("version") == 4:
                    self._load_bundle(bundle)
                    self._ext_enc = self._try_load_external_encoding()
                    self._loaded_from_cache = True
                    print(f"[AIModel] Loaded cached model: {self.model_path}")
                    return
                else:
                    print("[AIModel] Cache exists but signature/version mismatch. Retraining…")
            except Exception as e:
                print(f"[AIModel] Failed to load cache ({e}). Retraining…")

        # Train fresh model (and save)
        training_data = self.process_data(self._load_training_data())
        self._train_and_cache(training_data, excel_sig)
        self._ext_enc = self._try_load_external_encoding()

    def _load_training_data(self) -> pd.DataFrame:
        """Load both Harish workbooks and return one aligned data frame."""
        original, updated = [pd.read_excel(path) for path in self.excel_paths]
        updated = updated.rename(columns={"Unit Brand": "Manufacturer"})
        original = original.drop(columns=["Product Type.1"], errors="ignore")
        updated = updated.drop(columns=[
            "Address", "Claimed Employer", "Claimed Employer Type",
            "Claimed Position", "Credit Info ID", "EV Employer",
            "EV Employer Type", "EV Position", "Gender", "No of Dependents",
        ], errors="ignore")
        if "Borrower Type" not in original:
            original["Borrower Type"] = "Principal"
        shared_columns = [column for column in original.columns if column in updated.columns]
        if not shared_columns:
            raise ValueError("The two training workbooks have no shared columns.")
        combined = pd.concat(
            [original[shared_columns], updated[shared_columns]],
            ignore_index=True,
        )
        combined = combined.drop(
            columns=["Contract ID", "Party No", "Application No"],
            errors="ignore",
        )
        return combined.drop_duplicates().reset_index(drop=True)

    @staticmethod
    def _clean_income(value: Any) -> float:
        if pd.isna(value):
            return np.nan
        text = str(value).lower().strip()
        if any(word in text for word in (
            "confidential", "not disclosed", "not provided", "proof",
            "coec", "pls refer", "cannot disclose",
        )):
            return np.nan
        text = text.replace(",", "")
        text = re.sub(r"(\d+)k", r"\g<1>000", text)
        numbers = re.findall(r"\d+(?:\.\d+)?", text)
        if len(numbers) == 1:
            amount = float(numbers[0])
            return amount / 12 if "annual" in text else amount
        if len(numbers) >= 2:
            return float(np.mean([float(numbers[0]), float(numbers[1])]))
        return np.nan

    @staticmethod
    def _clean_tenure(value: Any) -> float:
        if pd.isna(value):
            return np.nan
        text = str(value).lower().strip().replace("?", "")
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return float(text)
        years = re.search(r"(\d+)\s*(?:year|years|yr|yrs)", text)
        months = re.search(r"(\d+)\s*(?:month|months|mos)", text)
        if years or months:
            return float((int(years.group(1)) if years else 0) * 12 + (int(months.group(1)) if months else 0))
        numbers = re.findall(r"\d+(?:\.\d+)?", text)
        return float(numbers[0]) if numbers else np.nan

    @classmethod
    def process_data(cls, data: pd.DataFrame) -> pd.DataFrame:
        """Apply the notebook's cleaning and feature engineering."""
        data = data.copy().rename(columns={"Current DPD": "Longest_DPD"})
        for column in ("Claimed Income", "EV Income", "BV Income"):
            if column in data:
                data[column] = data[column].apply(cls._clean_income)
        for column in ("Claimed Tenure", "EV Tenure", "BV Tenure", "Residence Tenure"):
            if column in data:
                data[column] = data[column].apply(cls._clean_tenure)
        for column in ("BAP Amount", "EV Income", "EV Tenure", "BV Income", "Price Gap", "BV Tenure", "DSCR", "Claimed Tenure", "Claimed Income", "Residence Tenure"):
            if column in data:
                data[f"{column}_missing"] = data[column].isna().astype(int)
                data[column] = pd.to_numeric(data[column], errors="coerce").fillna(-999)
        for column in cls.CATEGORICAL_COLS:
            if column in data:
                data[column] = data[column].fillna("Unknown")
            else:
                data[column] = "Unknown"
        if "Contract Start Date" in data:
            dates = pd.to_datetime(data["Contract Start Date"], errors="coerce")
            data["Contract_Year"], data["Contract_Month"] = dates.dt.year, dates.dt.month
            data = data.drop(columns=["Contract Start Date"])
        if "Marital Status" in data:
            data["Marital Status"] = data["Marital Status"].replace({"Separated": "Without Partner", "Divorced": "Without Partner", "Single": "Single/Not Married", "Not Married": "Single/Not Married"})
            data = data[~data["Marital Status"].isin(["Partner", "Unspecified"])]
        data = data.drop(columns=["Birthday", "BAP Date"], errors="ignore")
        if "Longest_DPD" in data:
            data["Longest_DPD"] = pd.to_numeric(data["Longest_DPD"], errors="coerce").fillna(0)
            data["Target"] = (data["Longest_DPD"] > 30).astype(int)

        numeric_columns = ["BAP Amount", "EV Income", "EV Tenure", "BV Income", "Price Gap", "BV Tenure", "DSCR", "Claimed Tenure", "Claimed Income", "Residence Tenure", "Amount Finance", "Downpayment", "Payment Terms", "Interest Rate", "Loan Amort", "Age as of Contract", "Downpayment %"]
        for column in numeric_columns:
            if column not in data:
                data[column] = np.nan
            if f"{column}_missing" not in data:
                data[f"{column}_missing"] = 1
        for column in ("BAP Type", "Mode of Payment"):
            if column not in data:
                data[column] = "Unknown"
        numeric_columns = data.select_dtypes(include=["number"]).columns
        data[numeric_columns] = data[numeric_columns].replace(-999, np.nan)
        winsor_columns = [
            "Loan Amort", "Claimed Income", "Downpayment", "Amount Finance",
            "Residence Tenure", "BV Income", "EV Income", "BAP Amount",
            "Claimed Tenure", "Interest Rate", "Price Gap", "DSCR",
        ]
        for column in winsor_columns:
            if column in data:
                data[column] = data[column].clip(data[column].quantile(.01), data[column].quantile(.99))
        epsilon = 1e-9
        def divide(left, right):
            if left not in data or right not in data:
                return pd.Series(np.nan, index=data.index)
            return data[left] / data[right].replace(0, np.nan)
        data["DTI"] = divide("Loan Amort", "Claimed Income")
        data["Income_Gap"] = data["Claimed Income"] - data["BV Income"]
        data["LTV"] = data["Amount Finance"] / (data["Amount Finance"] + data["Downpayment"]).replace(0, np.nan)
        data["Repayment_Stress"] = divide("Loan Amort", "Amount Finance")
        data["BAP_to_Finance"] = divide("BAP Amount", "Amount Finance")
        data["BAP_Income_Risk"] = ((data["BAP Amount"] > 200000) & (data["Income_Gap"] < 0)).astype(int)
        data["BAP_Asset_Risk"] = ((data["BAP Amount"] > 200000) & (data["Price Gap"] < -50000)).astype(int)
        data["Collateral_Shortfall"] = (-data["Price Gap"]).clip(lower=0) / (data["Amount Finance"] + epsilon)
        data["Rate_x_Term"] = data["Interest Rate"] * data["Payment Terms"]
        data["Equity_Cushion"] = data["Downpayment"] / (data["Downpayment"] + data["Amount Finance"] + epsilon)
        data["Shortfall_x_Term"] = data["Collateral_Shortfall"] * data["Payment Terms"]
        data["Income_Gap_x_LTV"] = data["Income_Gap"] * data["LTV"]
        data["DTI_x_LTV"] = data["DTI"] * data["LTV"]
        data["DP_to_Income"] = divide("Downpayment", "Claimed Income")
        data["Age_at_Maturity"] = data["Age as of Contract"] + data["Payment Terms"] / 12
        data["High_DTI"] = (data["DTI"] > data["DTI"].quantile(.75)).astype(int)
        data["Tenure_Mismatch"] = (data["Claimed Tenure"] - data["BV Tenure"]).abs()
        data["Income_Inconsistency"] = (data["BV Income"] / (data["Claimed Income"] + epsilon)).clip(upper=5)
        verification_columns = ["EV Income", "BV Income", "EV Tenure", "BV Tenure", "Price Gap", "DSCR", "Claimed Income", "Claimed Tenure"]
        data["Verification_Gaps"] = sum(data[column].isna().astype(int) for column in verification_columns if column in data)
        data["High_Risk_Missing"] = ((data.get("BV Tenure_missing", 0) == 1) & (data.get("Claimed Tenure_missing", 0) == 1)).astype(int)
        data["Unverified_Income_AND_Tenure"] = ((data.get("BV Income_missing", 0) == 1) & (data.get("Claimed Tenure_missing", 0) == 1)).astype(int)
        data["Long_Term_Loan"] = (data["Payment Terms"] >= 37).astype(int)
        downpayment_percent = data["Downpayment %"]
        data["Danger_DP_Band"] = ((downpayment_percent >= 15) & (downpayment_percent < 20)).astype(int)
        data["Safe_DP"] = (downpayment_percent >= 30).astype(int)
        data["LongTerm_x_DangerDP"] = ((data["Payment Terms"] >= 37) & (downpayment_percent >= 15) & (downpayment_percent < 20)).astype(int)
        data["BAP_Adverse_Loans_Only"] = (data["BAP Type"] == "Adverse Loans").astype(int)
        mop_risk = {"OTC - Bank": 4, "OTC - Gcash (Merchant)": 3, "ADA - Security": 3, "OTC": 3, "ADA - BPI": 2, "ADA - RCBC": 2, "ADA - BDO": 2, "ADA - Metrobank": 1, "PDC": 1, "ADA - Eastwest": 0, "Salary Deduction": 0, "OTC - Gcash (Bank Transfer)": 0}
        data["MOP_Risk_Score"] = data["Mode of Payment"].map(mop_risk).fillna(1)
        data["High_Risk_MOP"] = data["Mode of Payment"].isin(["OTC", "ADA - Security", "OTC - Gcash (Merchant)"]).astype(int)
        loan_history_risk = {
            "With history of Pastdue": 3, "Poor Handling": 3,
            "Loans and other credit dealings seen on CIC": 2,
            "Existing client of JFP less than 25% Paid": 2,
            "Repeat clients of other Banks and Finances": 1,
            "Existing client of JFP 25% and above Paid": 1,
            "Existing client of JFP 50% and above Paid": 0,
            "Fully paid Good Repeat Client": 0,
        }
        data["Loan_History_Risk"] = data["Loan History"].map(loan_history_risk).fillna(1)
        data["HighRiskMOP_x_DealerTier"] = np.nan
        return data.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)

    def process_raw_input(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the same cleaning steps to one raw customer row."""
        processed = self.process_data(pd.DataFrame([row_dict]))
        if processed.empty:
            raise ValueError("Customer input produced no row after preprocessing.")
        return processed.drop(columns=["Longest_DPD", "Target"], errors="ignore").iloc[0].to_dict()


    # ---------- external encoding (optional) ----------
    def _try_load_external_encoding(self):
        """
        Looks for encoding_report/encoding_maps.json next to the app bundle.
        Returns a dict with:
            cat_maps, fallback_code, features_order, categorical_cols, numeric_cols,
            lower_vocab, builtin_aliases, user_aliases
        or None if not found.
        """
        try:
            enc_path = resource_path(os.path.join("encoding_report", "encoding_maps.json"))
            if not os.path.exists(enc_path):
                print("[AIModel] encoding_maps.json not found; using built-in encoding.")
                return None
            with open(enc_path, "r", encoding="utf-8") as f:
                enc = json.load(f)

            cat_maps = enc["categorical_maps"]          # {col: {label: code}}
            fallback_code = enc["fallback_code"]        # {col: code}
            features_order = enc["features_order"]
            categorical_cols = list(cat_maps.keys())
            numeric_cols = [c for c in features_order if c not in categorical_cols]
            lower_vocab = {col: {k.lower(): k for k in m.keys()} for col, m in cat_maps.items()}

            # Built-in aliases (your list)
            builtin_aliases = {
                "Citizenship  - type": {
                    "filipino": "Philippines", "philippines": "Philippines", "ph": "Philippines", "pinoy": "Philippines",
                },
                "Product Type": {
                    "used": "Auto Loan (Second Hand)", "second hand": "Auto Loan (Second Hand)",
                    "second-hand": "Auto Loan (Second Hand)",
                },
                "Submitted ID   - type": {"primary": "ID2", "id2": "ID2"},
                "Co-Borrowers": {"yes": "Yes", "no": "No", "1": "1", "0": "0"},
                "Mode of Payment": {
                    "pdc": "Post Dated Checks",
                    "post dated checks": "Post Dated Checks",
                    "post-dated checks": "Post Dated Checks",
                    "auto-debit": "Auto Debit Arrangement",
                },
                "Employment Type  - type": {
                    "locally employed": "Locally employed",
                    "self-employed": "Self-Employed", "self employed": "Self-Employed",
                    "self employed and employed": "Self-Employed and Employed",
                },
                "Home Ownership - TYPE": {"owned": "Owned", "renting": "Renting", "rent": "Renting"},
                "LRD": {"low": "Low", "normal": "Normal", "high": "High"},
            }

            # Optional user aliases CSV (column,alias,canonical)
            def load_user_aliases(csv_rel="encoding_report/aliases.csv"):
                try:
                    csv_path = resource_path(csv_rel)
                    if not os.path.exists(csv_path):
                        return {}
                    df = pd.read_csv(csv_path)
                    user = {}
                    for _, r in df.iterrows():
                        col = str(r["column"]).strip()
                        alias = str(r["alias"]).strip()
                        canon = str(r["canonical"]).strip()
                        user.setdefault(col, {})[alias.lower()] = canon
                    return user
                except Exception:
                    return {}

            user_aliases = load_user_aliases()

            print("[AIModel] Loaded external encoding maps.")
            return {
                "cat_maps": cat_maps,
                "fallback_code": fallback_code,
                "features_order": features_order,
                "categorical_cols": categorical_cols,
                "numeric_cols": numeric_cols,
                "lower_vocab": lower_vocab,
                "builtin_aliases": builtin_aliases,
                "user_aliases": user_aliases,
            }
        except Exception as e:
            print(f"[AIModel] Failed to load external encoding maps: {e}")
            return None

    def _alias_lookup(self, col: str, sval: str) -> Optional[str]:
        if not self._ext_enc: return None
        low = sval.lower().strip()
        ua = self._ext_enc["user_aliases"]
        ba = self._ext_enc["builtin_aliases"]
        if col in ua and low in ua[col]: return ua[col][low]
        if col in ba and low in ba[col]: return ba[col][low]
        return None

    def _normalize_label(self, col: str, val) -> str:
        """
        Normalize raw string to training label:
          - Missing -> 'Missing'
          - numeric -> numeric-like label if present in training map
          - alias map -> canonical label
          - case-insensitive exact match -> canonical label
        """
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return "Missing"
        sval = str(val).strip()

        # If training used numeric-like labels ("0","1") and user gave numeric, map to that string label
        if self._ext_enc and col in self._ext_enc["cat_maps"] and isinstance(val, (int, float, np.integer, np.floating)):
            if float(val).is_integer():
                k = str(int(val))
                if k in self._ext_enc["cat_maps"][col]:
                    return k

        canon = self._alias_lookup(col, sval)
        if canon:
            return canon

        if self._ext_enc and col in self._ext_enc["lower_vocab"]:
            low = sval.lower()
            lv = self._ext_enc["lower_vocab"][col]
            if low in lv:
                return lv[low]

        return sval

    def _fuzzy_match_label(self, col: str, sval: str, cutoff=0.92) -> Optional[str]:
        if not self._ext_enc or col not in self._ext_enc["cat_maps"]: return None
        choices = list(self._ext_enc["cat_maps"][col].keys())
        got = difflib.get_close_matches(sval, choices, n=1, cutoff=cutoff)
        return got[0] if got else None

    def _map_categorical_to_code_ext(self, col: str, val, notes: list) -> int:
        mapping = self._ext_enc["cat_maps"][col]                 # label -> code
        fb = int(self._ext_enc["fallback_code"][col])
        valid_codes = set(mapping.values())

        # Code already?
        if isinstance(val, (int, np.integer)) and int(val) in valid_codes:
            return int(val)
        if isinstance(val, (float, np.floating)) and val.is_integer() and int(val) in valid_codes:
            return int(val)
        if isinstance(val, str) and val.isdigit() and int(val) in valid_codes:
            return int(val)

        cand = self._normalize_label(col, val)

        if cand in mapping:  # direct label hit
            return mapping[cand]

        close = self._fuzzy_match_label(col, cand, cutoff=0.92)
        if close and close in mapping:
            if cand != close:
                notes.append(f"[fuzzy:{col}] '{cand}' -> '{close}'")
            return mapping[close]

        notes.append(f"[fallback:{col}] '{val}' -> code {fb}")
        return fb

    def _normalize_numeric_ext(self, col: str, val, notes: list) -> float:
        # Exact Colab parity:
        if col == "Contract Start Date":
            dt = pd.to_datetime(val, format="%m/%d/%Y", errors="coerce")
            if pd.isna(dt):
                dt = pd.to_datetime(val, errors="coerce")
            return 0.0 if pd.isna(dt) else float(dt.value)  # epoch ns

        if col == "DSCR - %":
            num = pd.to_numeric(val, errors="coerce")
            if pd.isna(num): return 0.0
            x = float(num)
            # If user put "43.147" meaning 43.147%, scale to 0.43147
            if 1.5 < x <= 200:
                notes.append(f"[scale:{col}] {x} -> {x/100.0}")
                return x / 100.0
            return x

        num = pd.to_numeric(val, errors="coerce")
        return float(0.0 if pd.isna(num) else num)

    def _encode_with_external(self, row_dict: Dict[str, Any], verbose=False) -> pd.DataFrame:
        notes, row = [], {}
        # Use the external features_order to build the vector
        feat_order = self._ext_enc["features_order"]
        cat_cols = set(self._ext_enc["categorical_cols"])
        for col in feat_order:
            val = row_dict.get(col, None)
            if col in cat_cols:
                row[col] = self._map_categorical_to_code_ext(col, val, notes)
            else:
                row[col] = self._normalize_numeric_ext(col, val, notes)
        if verbose and notes:
            print("\n".join(notes))
        # Finally, reindex to the model's training order (self.features)
        df = pd.DataFrame([row])
        df = df.reindex(columns=self.features, fill_value=0)  # <— ensure exact training order
        return df

    # ---------- training path ----------
    def _fit_harish_splits(self, train_data, val_data, test_data, train_target):
        from sklearn.model_selection import KFold

        global_mean = float(train_target.mean())
        train = train_data.drop(columns=["Longest_DPD", "Target"], errors="ignore").copy()
        val = val_data.drop(columns=["Longest_DPD", "Target"], errors="ignore").copy()
        test = test_data.drop(columns=["Longest_DPD", "Target"], errors="ignore").copy()
        drop_high_card = ["Dealer Name", "Asset", "Manufacturer", "Loan History", "BAP Type"]

        dealer = "Dealer Name"
        if dealer in train:
            stats = pd.DataFrame({"target": train_target.values, "dealer": train[dealer].astype(str).values}).groupby("dealer")["target"].agg(["mean", "count"])
            smooth = (stats["mean"] * stats["count"] + global_mean * 10) / (stats["count"] + 10)
            rates = []
            for part in (train, val, test):
                rates.append(part[dealer].astype(str).map(smooth).fillna(global_mean))
            for part, rate in zip((train, val, test), rates):
                part["Dealer_Default_Rate"] = rate.to_numpy()
                part["LoanHistory_x_DealerRisk"] = part["Loan_History_Risk"] * rate.to_numpy()
                part["Dealer_x_LowDP"] = rate.to_numpy() * (1 - part["Downpayment"] / 100)
                part["Dealer_x_Term"] = rate.to_numpy() * part["Payment Terms"]
            high, mid = smooth.quantile(.90), smooth.quantile(.70)
            self.dealer_smooth = smooth.to_dict()
            self.dealer_high_cutoff = float(high)
            self.dealer_mid_cutoff = float(mid)
            self.dealer_dti_cutoff = float(train["DTI"].quantile(.30))
            for part, rate in zip((train, val, test), rates):
                tier = pd.cut(rate, [-np.inf, mid, high, np.inf], labels=[0, 1, 2]).astype(int)
                part["Dealer_Risk_Tier"] = tier.to_numpy()
                part["High_Risk_Dealer"] = (tier == 2).astype(int).to_numpy()
                part["Mid_Risk_Dealer"] = (tier == 1).astype(int).to_numpy()
                part["GoodBorrower_RiskyDealer"] = ((tier >= 1) & (part["DTI"] < train["DTI"].quantile(.30))).astype(int).to_numpy()
                part["HighRiskMOP_x_DealerTier"] = part["High_Risk_MOP"] * tier.to_numpy()

        target_maps = {}
        kfold = KFold(n_splits=5, shuffle=True, random_state=42)
        for column in self.HARISH_TE_COLS:
            if column not in train:
                continue
            grouped = pd.DataFrame({"target": train_target.values, "value": train[column].astype(str).values}).groupby("value")["target"].agg(["mean", "count"])
            mapping = ((grouped["mean"] * grouped["count"] + global_mean * 20) / (grouped["count"] + 20)).to_dict()
            target_maps[column] = mapping
            oof = np.full(len(train), global_mean, dtype=float)
            values = train[column].astype(str).reset_index(drop=True)
            targets = train_target.reset_index(drop=True)
            for fit_idx, hold_idx in kfold.split(values):
                fold = pd.DataFrame({"target": targets.iloc[fit_idx].values, "value": values.iloc[fit_idx].values}).groupby("value")["target"].agg(["mean", "count"])
                fold_map = ((fold["mean"] * fold["count"] + global_mean * 20) / (fold["count"] + 20)).to_dict()
                oof[hold_idx] = values.iloc[hold_idx].map(fold_map).fillna(global_mean)
            train[f"{column}_TE"] = oof
            val[f"{column}_TE"] = val[column].astype(str).map(mapping).fillna(global_mean).to_numpy()
            test[f"{column}_TE"] = test[column].astype(str).map(mapping).fillna(global_mean).to_numpy()

        dealer_features = {
            "Dealer_Default_Rate", "LoanHistory_x_DealerRisk", "Dealer_x_LowDP",
            "Dealer_x_Term", "High_Risk_Dealer", "Mid_Risk_Dealer",
            "Dealer_Risk_Tier", "GoodBorrower_RiskyDealer",
            "HighRiskMOP_x_DealerTier",
        }
        drop_columns = set(drop_high_card) | (self.HARISH_DROP_COLS - dealer_features)
        for part in (train, val, test):
            part.drop(columns=[c for c in drop_columns if c in part], inplace=True)
        categorical = [c for c in self.CATEGORICAL_COLS if c in train.columns and c not in drop_high_card]
        category_maps = {}
        for column in categorical:
            values = pd.concat([train[column], val[column], test[column]]).fillna("Unknown").astype(str)
            mapping = {value: code for code, value in enumerate(sorted(values.unique()))}
            category_maps[column] = mapping
            for part in (train, val, test):
                part[column] = part[column].fillna("Unknown").astype(str).map(mapping).fillna(-1)

        train = train.apply(pd.to_numeric, errors="coerce")
        val = val.apply(pd.to_numeric, errors="coerce")
        test = test.apply(pd.to_numeric, errors="coerce")
        impute_columns = [c for c in ("Claimed Income", "Claimed Tenure", "DSCR", "Residence Tenure") if c in train]
        if impute_columns:
            imputer = IterativeImputer(estimator=RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1), max_iter=5, random_state=42)
            train[impute_columns] = imputer.fit_transform(train[impute_columns])
            val[impute_columns] = imputer.transform(val[impute_columns])
            test[impute_columns] = imputer.transform(test[impute_columns])
        medians = train.median().fillna(0)
        train, val, test = train.fillna(medians), val.fillna(medians), test.fillna(medians)

        scores, thresholds = {}, {}
        for column in train.columns:
            values = train[column].to_numpy(float)
            cuts = np.percentile(values, np.linspace(5, 95, 50))
            best_score, best_cut = 0.0, None
            for cut in np.unique(cuts):
                left, right = train_target.to_numpy()[values <= cut], train_target.to_numpy()[values > cut]
                if len(left) < 5 or len(right) < 5:
                    continue
                pooled = np.sqrt((left.var() + right.var()) / 2)
                score = abs(left.mean() - right.mean()) / pooled if pooled else 0
                if score > best_score:
                    best_score, best_cut = score, cut
            scores[column] = best_score
            if best_score > 0.5:
                thresholds[column] = float(best_cut)
        for column, threshold in thresholds.items():
            name = f"{column}_cd_split"
            train[name] = (train[column] <= threshold).astype(int)
            val[name] = (val[column] <= threshold).astype(int)
            test[name] = (test[column] <= threshold).astype(int)
        redundant = ["LoanHistory_x_DealerRisk_cd_split", "Dealer_x_LowDP_cd_split", "Dealer_Default_Rate_cd_split", "Dealer_x_Term_cd_split", "GoodBorrower_RiskyDealer_cd_split", "High_Risk_Dealer_cd_split", "HighRiskMOP_x_DealerTier_cd_split", "High_DTI", "GoodBorrower_RiskyDealer"]
        train.drop(columns=[c for c in redundant if c in train], inplace=True)
        val.drop(columns=[c for c in redundant if c in val], inplace=True)
        test.drop(columns=[c for c in redundant if c in test], inplace=True)
        features = sorted(train.columns, key=lambda column: scores.get(column, 0), reverse=True)
        return train[features], val.reindex(columns=features, fill_value=0), test.reindex(columns=features, fill_value=0), target_maps, category_maps, global_mean, medians, thresholds, imputer if impute_columns else None

    def _fit_harish_features(self, data: pd.DataFrame):
        """Fit categorical mappings and target encodings on the training split."""
        target = data["Target"].astype(int)
        features = data.drop(columns=["Longest_DPD", "Target"], errors="ignore").copy()
        features = features.drop(columns=[c for c in self.HARISH_DROP_COLS if c in features], errors="ignore")
        categorical = [c for c in self.CATEGORICAL_COLS if c in features.columns]
        global_mean = float(target.mean())
        target_maps = {}
        for column in self.HARISH_TE_COLS:
            if column not in features.columns:
                continue
            grouped = target.groupby(features[column].astype(str)).agg(["mean", "count"])
            target_maps[column] = {
                str(key): float((row["mean"] * row["count"] + global_mean * 20) /
                                (row["count"] + 20))
                for key, row in grouped.iterrows()
            }
            features[f"{column}_TE"] = features[column].astype(str).map(target_maps[column]).fillna(global_mean)

        category_maps = {}
        for column in categorical:
            values = features[column].fillna("Unknown").astype(str)
            mapping = {value: code for code, value in enumerate(sorted(values.unique()))}
            category_maps[column] = mapping
            features[column] = values.map(mapping).astype(float)

        features = features.apply(pd.to_numeric, errors="coerce")
        medians = features.median().fillna(0.0)
        features = features.fillna(medians)

        split_thresholds = {}
        for column in features.columns:
            values = features[column].to_numpy(dtype=float)
            thresholds = np.percentile(values, np.linspace(5, 95, 50))
            best_score, best_threshold = 0.0, None
            for threshold in np.unique(thresholds):
                left = target[features[column] <= threshold]
                right = target[features[column] > threshold]
                if len(left) < 5 or len(right) < 5:
                    continue
                pooled = np.sqrt((left.var() + right.var()) / 2)
                score = abs(left.mean() - right.mean()) / pooled if pooled > 0 else 0.0
                if score > best_score:
                    best_score, best_threshold = float(score), float(threshold)
            if best_score > 0.5:
                split_thresholds[column] = best_threshold
                features[f"{column}_cd_split"] = (features[column] <= best_threshold).astype(int)

        dropped_columns = [c for c in self.HARISH_DROP_COLS if c in data.columns]
        return features, target_maps, category_maps, medians.to_dict(), split_thresholds, dropped_columns

    def _encode_harish_input(self, row_dict: Dict[str, Any]) -> pd.DataFrame:
        frame = self.process_data(pd.DataFrame([row_dict]))
        frame = frame.drop(columns=["Longest_DPD", "Target"], errors="ignore")
        dealer = "Dealer Name"
        if dealer in frame and getattr(self, "dealer_smooth", None):
            rate = frame[dealer].astype(str).map(self.dealer_smooth).fillna(self.global_mean)
            tier = pd.cut(
                rate,
                [-np.inf, self.dealer_mid_cutoff, self.dealer_high_cutoff],
                labels=[0, 1],
            ).astype(float).fillna(2)
            frame["Dealer_Default_Rate"] = rate
            frame["LoanHistory_x_DealerRisk"] = frame["Loan_History_Risk"] * rate
            frame["Dealer_x_LowDP"] = rate * (1 - frame["Downpayment"] / 100)
            frame["Dealer_x_Term"] = rate * frame["Payment Terms"]
            frame["Dealer_Risk_Tier"] = tier
            frame["High_Risk_Dealer"] = (tier == 2).astype(int)
            frame["Mid_Risk_Dealer"] = (tier == 1).astype(int)
            frame["GoodBorrower_RiskyDealer"] = ((tier >= 1) & (frame["DTI"] < self.dealer_dti_cutoff)).astype(int)
            frame["HighRiskMOP_x_DealerTier"] = frame["High_Risk_MOP"] * tier
        for column, mapping in self.target_maps.items():
            if column in frame:
                frame[f"{column}_TE"] = frame[column].astype(str).map(mapping).fillna(self.global_mean)
        frame = frame.drop(columns=[c for c in self.dropped_columns if c in frame], errors="ignore")
        for column, mapping in self.category_maps.items():
            if column in frame:
                frame[column] = frame[column].fillna("Unknown").astype(str).map(mapping).fillna(-1)
        frame = frame.reindex(columns=self.base_features, fill_value=np.nan)
        if self.imputer is not None:
            impute_columns = [c for c in ("Claimed Income", "Claimed Tenure", "DSCR", "Residence Tenure") if c in frame]
            if impute_columns:
                frame[impute_columns] = self.imputer.transform(frame[impute_columns])
        for column, threshold in self.split_thresholds.items():
            split_column = f"{column}_cd_split"
            if column in frame and split_column in self.features:
                frame[split_column] = (frame[column] <= threshold).astype(int)
        frame = frame.reindex(columns=self.features, fill_value=np.nan)
        return frame.apply(pd.to_numeric, errors="coerce").fillna(self.medians)

    # ---------- Harish training and loading ----------
    def _train_and_cache(self, data: pd.DataFrame, excel_sig: str) -> None:
        if "Target" not in data.columns:
            raise ValueError("Processed data is missing the Target column.")
        train_val, test_data = train_test_split(
            data, test_size=0.10, random_state=42, stratify=data["Target"]
        )
        train_data, val_data = train_test_split(
            train_val, test_size=0.111, random_state=42, stratify=train_val["Target"]
        )
        train_target = train_data["Target"].astype(int).reset_index(drop=True)
        val_target = val_data["Target"].astype(int).reset_index(drop=True)
        test_target = test_data["Target"].astype(int).reset_index(drop=True)
        train_encoded, val_encoded, test_encoded, target_maps, category_maps, global_mean, medians, split_thresholds, imputer = self._fit_harish_splits(
            train_data.reset_index(drop=True), val_data.reset_index(drop=True), test_data.reset_index(drop=True), train_target
        )
        self.global_mean = global_mean
        self.target_maps = target_maps
        self.category_maps = category_maps
        dealer_features = {
            "Dealer_Default_Rate", "LoanHistory_x_DealerRisk", "Dealer_x_LowDP",
            "Dealer_x_Term", "High_Risk_Dealer", "Mid_Risk_Dealer",
            "Dealer_Risk_Tier", "GoodBorrower_RiskyDealer",
            "HighRiskMOP_x_DealerTier",
        }
        self.dropped_columns = list((set(self.HARISH_DROP_COLS) - dealer_features) | {
            "Dealer Name", "Asset", "Manufacturer", "Loan History", "BAP Type",
        })
        self.medians = medians.reindex(train_encoded.columns).fillna(0.0)
        self.imputer = imputer
        self.base_features = [c for c in train_encoded.columns if not c.endswith("_cd_split")]
        self.split_thresholds = split_thresholds
        self.features = list(train_encoded.columns)

        model = LGBMClassifier(**self.HARISH_BEST_PARAMS, random_state=42, verbose=-1,
                               deterministic=True, force_row_wise=True)
        threshold_model = CalibratedClassifierCV(estimator=model, method="isotonic", cv=5)
        threshold_model.fit(train_encoded, train_target)
        probabilities = threshold_model.predict_proba(val_encoded)[:, 1]
        fpr, _, thresholds = roc_curve(val_target, probabilities)
        valid = np.where(fpr <= 0.035)[0]
        threshold = float(thresholds[valid[-1]]) if len(valid) else 0.5
        final_train = pd.concat([train_encoded, val_encoded], ignore_index=True)
        final_target = pd.concat([train_target, val_target], ignore_index=True)
        final_model = CalibratedClassifierCV(
            estimator=LGBMClassifier(**self.HARISH_BEST_PARAMS, random_state=42,
                                     verbose=-1, deterministic=True, force_row_wise=True),
            method="isotonic", cv=5,
        )
        final_model.fit(final_train, final_target)
        auc = float(roc_auc_score(test_target, final_model.predict_proba(test_encoded)[:, 1]))

        self.model = final_model
        self.rf = final_model
        self.X_full = final_train.reset_index(drop=True)
        self.categorical_cols = [c for c in self.CATEGORICAL_COLS if c in self.features]
        self.numeric_cols = [c for c in self.features if c not in self.categorical_cols]
        bundle = {
            "version": 4, "excel_sha1": excel_sig, "model": final_model,
            "features": self.features, "base_features": self.base_features,
            "categorical_cols": self.categorical_cols, "numeric_cols": self.numeric_cols,
            "target_maps": target_maps, "category_maps": category_maps,
            "global_mean": self.global_mean, "medians": self.medians.to_dict(),
            "imputer": imputer, "split_thresholds": split_thresholds, "dropped_columns": self.dropped_columns,
            "dealer_smooth": getattr(self, "dealer_smooth", {}),
            "dealer_high_cutoff": getattr(self, "dealer_high_cutoff", 0.0),
            "dealer_mid_cutoff": getattr(self, "dealer_mid_cutoff", 0.0),
            "dealer_dti_cutoff": getattr(self, "dealer_dti_cutoff", 0.0),
            "decision_threshold": threshold, "auc": auc, "X_full": self.X_full,
        }
        joblib.dump(bundle, self.model_path, compress=3)
        self._load_bundle(bundle)

    def _load_bundle(self, bundle: dict) -> None:
        self.model = bundle.get("model", bundle.get("rf"))
        self.rf = self.model
        self.features = bundle["features"]
        self.base_features = bundle.get("base_features", self.features)
        self.categorical_cols = bundle.get("categorical_cols", [])
        self.numeric_cols = bundle.get("numeric_cols", [])
        self.target_maps = bundle.get("target_maps", {})
        self.category_maps = bundle.get("category_maps", {})
        self.global_mean = bundle.get("global_mean", 0.0)
        self.medians = pd.Series(bundle.get("medians", {})).reindex(self.features).fillna(0.0)
        self.imputer = bundle.get("imputer")
        self.dealer_smooth = bundle.get("dealer_smooth", {})
        self.dealer_high_cutoff = bundle.get("dealer_high_cutoff", 0.0)
        self.dealer_mid_cutoff = bundle.get("dealer_mid_cutoff", 0.0)
        self.dealer_dti_cutoff = bundle.get("dealer_dti_cutoff", 0.0)
        self.split_thresholds = bundle.get("split_thresholds", {})
        self.dropped_columns = bundle.get("dropped_columns", [])
        self.decision_threshold = bundle.get("decision_threshold", 0.5)
        self.auc = bundle.get("auc", float("nan"))
        self.X_full = bundle.get("X_full")
        self._explainer = None

    # ---------- SHAP explainer(lazy) - ---------

    def ensure_explainer(self):
        """
        Build a TreeExplainer once, using the feature-matrix X as background.
        Keep model_output='raw' and disable additivity checks to match your Colab.
        """
        if self._explainer is not None:
            return self._explainer
        if self.X_full is None or len(self.X_full) == 0:
            raise RuntimeError("Background X_full not available for SHAP explainer.")
        X_bg = self.X_full[self.features]
        explain_model = self.model.calibrated_classifiers_[0].estimator
        self._explainer = shap.TreeExplainer(
            explain_model,
            data=X_bg,
            model_output="raw"
        )
        return self._explainer

    def breakdown_for_features(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns SHAP breakdown for a single sample.
        Output:
          {
            'base_value': float,
            'prediction': float,
            'reconstructed': float,   # base + sum(shap)
            'rows': [ { 'feature', 'value', 'shap', 'abs_shap' }, ... ] (sorted desc by abs_shap)
          }
        """
        # Prepare one-row DF in exact training order
        df = self._prepare_inference_df(row_dict)

        # Build explainer (lazy)
        explainer = self.ensure_explainer()

        # SHAP for this row
        shap_vals = explainer.shap_values(df, check_additivity=False)
        shap_vec = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
        expected = explainer.expected_value
        base = float(expected[1] if isinstance(expected, (list, np.ndarray)) else expected)
        recon = float(base + shap_vec.sum())
        pred = float(self.model.predict_proba(df[self.features])[0, 1])

        # Build rows with human values
        rows = []
        for j, feat in enumerate(self.features):
            # Prefer original (pre-encoded) value for display if present
            display_val = row_dict.get(feat, df.iloc[0, j])
            # Nice formatting for numbers/dates
            if isinstance(display_val, float):
                display_val = round(display_val, 4)
            rows.append({
                "feature": feat,
                "value": display_val,
                "shap": float(shap_vec[j]),
                "abs_shap": float(abs(shap_vec[j])),
            })

        # Sort by absolute impact, high → low
        rows.sort(key=lambda r: r["abs_shap"], reverse=True)

        return {
            "base_value": base,
            "prediction": pred,
            "reconstructed": recon,
            "rows": rows,
        }

    def _prepare_inference_df(self, row_dict: Dict[str, Any]) -> pd.DataFrame:
        return self._encode_harish_input(row_dict)

    def predict_from_features(self, row_dict: Dict[str, Any]) -> float:
        """Return the calibrated probability that the customer defaults."""
        frame = self._prepare_inference_df(row_dict)
        return float(self.model.predict_proba(frame)[0, 1])

    def predict_by_index(self, idx: int) -> float:
        if self.X_full is None or idx < 0 or idx >= len(self.X_full):
            raise IndexError(f"Index {idx} out of bounds for X with length {len(self.X_full)}")
        return float(self.model.predict_proba(self.X_full.iloc[[idx]])[0, 1])