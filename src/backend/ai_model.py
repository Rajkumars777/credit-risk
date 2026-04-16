import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../..')))

import hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
import joblib

try:
    import shap
except ImportError:
    shap = None
import json, difflib

def resource_path(rel_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    PyInstaller bundles with these mappings:
      src/data/img -> img/
      src/data/dataset -> dataset/
      src/data/database -> database/
    """
    if getattr(sys, "frozen", False):
        # In frozen mode, files are at root of _MEIPASS
        if rel_path.startswith("src/data/img/"):
            rel_path = rel_path.replace("src/data/img/", "img/")
        elif rel_path.startswith("src/data/dataset/"):
            rel_path = rel_path.replace("src/data/dataset/", "dataset/")
        elif rel_path.startswith("src/data/database/"):
            rel_path = rel_path.replace("src/data/database/", "database/")
        return os.path.join(sys._MEIPASS, rel_path)  # type: ignore[attr-defined]
    
    # Development mode
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    return os.path.join(project_root, rel_path)

def _get_models_dir() -> str:
    """Get path to models directory in a writable location.
    
    For PyInstaller (frozen), cache goes to user's home.
    For development, use the src/backend/models directory.
    """
    try:
        if getattr(sys, "frozen", False):
            # Running as PyInstaller executable - use user cache
            app_dir = os.path.join(os.path.expanduser("~"), ".jaccs_credit_app")
            models_dir = os.path.join(app_dir, "models_cache")
            os.makedirs(models_dir, exist_ok=True)
            return models_dir
        else:
            # Development mode
            models_dir = os.path.join(os.path.dirname(__file__), "models")
            os.makedirs(models_dir, exist_ok=True)
            return models_dir
    except Exception as e:
        print(f"[AIModel] Warning: Failed to create models directory ({e}). Using temp location.")
        # Fallback to a temp location if creation fails
        import tempfile
        return tempfile.gettempdir()

def _excel_sha1(path: str) -> str:
    """Fast-ish SHA1 of a file to detect changes."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _model_path_for_excel(excel_filename: str) -> str:
    """Where to store the cached model bundle."""
    base_dir = _get_models_dir()
    stem = Path(excel_filename).stem
    return str(Path(base_dir) / f"{stem}_rf.joblib")

class AIModel:
    # -- Static Variable --#
    TARGET = 'Longest DPD'
    features = [
        'Amount Financed - Amount',
        'Downpayment - Amount',
        'Payment Terms - Number',
        'Unit Brand   - Scoring Code',
        'Type of unit  - Scoring Code',
        'Price Gap - Scoring Code',
        'Loan History - Scoring Code',
        'BAP / CIC Findings - Scoring Code',
        'INCOME - Amount',
        'Employment Type  - type',
        'Employment / Business Tenure  - Scoring Code',
        'DSCR - %',
        'Home Ownership - TYPE',
        'Residence Tenure  - Scoring Code',
        'Citizenship  - type',
        'Type of dealer  - Scoring Code',
        'Submitted ID   - type',
        'Marital Status - Scoring Code',
        'Product Type',
        #'Contract Start Date',
        'Vehicle List Price',
        'LOAN AMORT',
        #'Mode of Payment',
        'Co-Borrowers',
        'Age'
        #'LRD'
    ]

    categorical_cols = [
        'Employment Type  - type',
        'Home Ownership - TYPE',
        'Citizenship  - type',
        'Submitted ID   - type',
        'Product Type',
        #'Mode of Payment',
        'Co-Borrowers'
        #'LRD'
    ]

    @staticmethod
    def make_balanced_dataset(df, target, random_seed):
        # Split into positive and negative classes
        df_pos = df[df[target] != 0]
        df_neg = df[df[target] == 0]

        # Find the size of the smaller class
        min_size = min(len(df_pos), len(df_neg))

        # Sample both classes equally
        df_pos_sampled = df_pos.sample(n=min_size, random_state=random_seed)
        df_neg_sampled = df_neg.sample(n=min_size, random_state=random_seed)

        # Combine and shuffle
        df_balanced = pd.concat([df_pos_sampled, df_neg_sampled]).sample(
            frac=1, random_state=random_seed
        ).reset_index(drop=True)

        return df_balanced

    @staticmethod
    def quantize_longest_dpd(x):
        try:
            if x <= 30:
                return 0 # 0 to 30
            else:
                return 1 # 31 and more
        except:
            return np.nan
        
    def __init__(self, excel_filename: str):
        # Resolve paths - ensure we use relative paths consistently
        # If an absolute path is passed, extract just the relative portion
        if os.path.isabs(excel_filename):
            # Try to extract relative path from absolute
            try:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
                excel_filename = os.path.relpath(excel_filename, project_root)
            except ValueError:
                pass  # Keep original if relpath fails
        
        self.excel_path = resource_path(excel_filename)
        self.model_path = _model_path_for_excel(excel_filename)
        self._loaded_from_cache = False
        self._explainer = None  # SHAP (lazy)

        # Try to load cached model first (only compute SHA1 if cache exists)
        if os.path.exists(self.model_path):
            try:
                bundle = joblib.load(self.model_path)
                # Try to validate against Excel SHA1, but don't fail if Excel is missing
                excel_sig = None
                try:
                    if os.path.exists(self.excel_path):
                        excel_sig = _excel_sha1(self.excel_path)
                except Exception:
                    pass  # Excel file not available, skip signature check
                
                # Load cache if version matches (skip SHA1 check if Excel is missing)
                if bundle.get("version") == 1:
                    if excel_sig is None or bundle.get("excel_sha1") == excel_sig:
                        self._load_bundle(bundle)
                        self._loaded_from_cache = True
                        print(f"[AIModel] Loaded cached model: {self.model_path}")
                        return
                    else:
                        print("[AIModel] Cache exists but Excel signature mismatch. Retraining…")
                else:
                    print("[AIModel] Cache exists but version mismatch. Retraining…")
            except Exception as e:
                print(f"[AIModel] Failed to load cache ({e}). Attempting to retrain…")

        # Train fresh model (and save) - Excel file is required here
        if not os.path.exists(self.excel_path):
            raise Exception(
                f"Training data Excel file not found: {self.excel_path}\n"
                f"Cached model also unavailable. Please provide the Excel training data file."
            )
        
        try:
            original_data = pd.read_excel(self.excel_path, engine='openpyxl')
        except Exception as e:
            error_msg = str(e)
            if "worksheet index 0 is invalid" in error_msg:
                raise Exception(f"Training data Excel file appears to be corrupted or empty: {self.excel_path}")
            elif "No worksheets found" in error_msg:
                raise Exception(f"Training data Excel file contains no worksheets: {self.excel_path}")
            else:
                raise Exception(f"Failed to load training data from {self.excel_path}: {error_msg}")
        
        # Train and cache the model
        excel_sig = _excel_sha1(self.excel_path)
        self._train_and_cache(excel_sig)

    def _train_and_cache(self, excel_sig: str) -> None:
        try:
            original_data = pd.read_excel(self.excel_path, engine='openpyxl')
        except Exception as e:
            error_msg = str(e)
            if "worksheet index 0 is invalid" in error_msg:
                raise Exception(f"Training data Excel file appears to be corrupted or empty: {self.excel_path}")
            elif "No worksheets found" in error_msg:
                raise Exception(f"Training data Excel file contains no worksheets: {self.excel_path}")
            else:
                raise Exception(f"Failed to load training data from {self.excel_path}: {error_msg}")
        
        data = original_data.copy()

        n_original = data.shape[0]
        print("Number of records originally loaded:", n_original)

        data['Original Longest DPD'] = data[self.TARGET]
        data[self.TARGET] = data[self.TARGET].apply(self.quantize_longest_dpd)

        needed_cols = self.features + ["Original Longest DPD", self.TARGET]
        data = data[needed_cols]

        # data['Contract Start Date'] = pd.to_datetime(data['Contract Start Date'], format='%m/%d/%Y', errors='coerce')
        # data['Contract Start Date'].fillna(pd.Timestamp(0), inplace=True)
        # data['Contract Start Date'] = data['Contract Start Date'].astype(int) / 10**9
        
        # Mending As per clients request 
        cols_to_drop = ['Contract Start Date', 'LRD', 'Mode of Payment']
        data = data.drop(columns=[col for col in cols_to_drop if col in data.columns])

        numerical_cols = [c for c in self.features if c not in self.categorical_cols]
        for col in numerical_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(float)

        data.drop_duplicates(inplace=True)

        le_dict = {}
        cat_maps = {}
        for col in self.categorical_cols:
            le = LabelEncoder()
            data[col] = le.fit_transform(data[col].astype(str))
            # Add 'Unknown' class for unseen categories
            le.classes_ = np.append(le.classes_, 'Unknown')
            le_dict[col] = le
            # Create mapping dict: label -> code
            cat_maps[col] = {label: code for code, label in enumerate(le.classes_)}

        df = data[self.features + [self.TARGET]].copy()
        df = df.astype({col: 'int' for col in self.categorical_cols + [self.TARGET]})

        print("Db size with Target value = 0 :", df[df[self.TARGET] == 0].shape)
        print("Db size with Target value != 0 :", df[df[self.TARGET] != 0].shape)

        df_balanced = self.make_balanced_dataset(df, self.TARGET, 4)

        print("After balance db Target value = 0 :", df_balanced[df_balanced[self.TARGET] == 0].shape)
        print("After balance db Target value != 0 :", df_balanced[df_balanced[self.TARGET] != 0].shape)

        X = df_balanced[self.features]
        y = df_balanced[self.TARGET]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )

        rf = RandomForestClassifier(n_estimators=300, random_state=2, n_jobs=-1, max_depth=25)
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)
        accuracy = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average='weighted'))
        print("Accuracy:", accuracy)
        print("F1 Score:", f1)

        # Save everything we need for inference
        bundle = {
            "version": 1,
            "excel_sha1": excel_sig,
            "rf": rf,
            "features": self.features,
            "categorical_cols": self.categorical_cols,
            "le_dict": le_dict,
            "cat_maps": cat_maps,
            "accuracy": accuracy,
            "f1": f1,
            "X_full": X.reset_index(drop=True),
            "original_df_cols": list(original_data.columns),
        }
        try:
            joblib.dump(bundle, self.model_path)
            print(f"[AIModel] Saved model bundle: {self.model_path}")
        except Exception as e:
            print(f"[AIModel] Failed to save bundle ({e})")

        # Load into self
        self._load_bundle(bundle)

    def _load_bundle(self, bundle: dict) -> None:
        self.rf = bundle["rf"]
        self.features = bundle["features"]
        self.categorical_cols = bundle["categorical_cols"]
        self.le_dict = bundle["le_dict"]
        self.cat_maps = bundle["cat_maps"]
        self.accuracy = bundle.get("accuracy", float("nan"))
        self.f1 = bundle.get("f1", float("nan"))
        self.X_full = bundle.get("X_full")  # used by predict_by_index
        # SHAP explainer is created lazily
        self._explainer = None

    def _prepare_inference_df(self, row_dict: Dict[str, Any]) -> pd.DataFrame:
        sample = dict(row_dict)
        for f in self.features:
            if f not in sample:
                sample[f] = 0
        df = pd.DataFrame([sample])

        # if "Contract Start Date" in df.columns:
        #     df['Contract Start Date'] = pd.to_datetime(df['Contract Start Date'], format='%m/%d/%Y', errors='coerce')
        #     df['Contract Start Date'].fillna(pd.Timestamp(0), inplace=True)
        #     df['Contract Start Date'] = df['Contract Start Date'].astype(int) / 10**9

        numerical_cols = [c for c in self.features if c not in self.categorical_cols]
        for col in numerical_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

        for col in self.categorical_cols:
            if col in df.columns:
                val = str(df[col].iloc[0])
                df[col] = self.cat_maps[col].get(val, self.cat_maps[col]['Unknown'])

        return df[self.features]

    def ensure_explainer(self):
        """
        Build a TreeExplainer once, using the feature-matrix X as background.
        """
        if self._explainer is not None:
            return self._explainer
        if shap is None:
            raise ImportError("SHAP is not installed. Install with: pip install shap")
        if self.X_full is None or len(self.X_full) == 0:
            raise ValueError("No training data available for SHAP explainer")
        X_bg = self.X_full[self.features]
        self._explainer = shap.TreeExplainer(
            self.rf,
            data=X_bg
        )
        return self._explainer

    def breakdown_for_features(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns SHAP breakdown for a single sample.
        Output:
          {
            'base_value': float,
            'prediction': int,
            'reconstructed': float,   # base + sum(shap)
            'rows': [ { 'feature', 'value', 'shap', 'abs_shap' }, ... ] (sorted desc by abs_shap)
          }
        """
        # Prepare one-row DF in exact training order
        df = self._prepare_inference_df(row_dict)

        # Build explainer (lazy)
        explainer = self.ensure_explainer()

        # SHAP for this row
        shap_vals = explainer.shap_values(df)
        print(f"SHAP vals shape: {np.asarray(shap_vals).shape}, type: {type(shap_vals)}")
        shap_vals = np.asarray(shap_vals)
        if shap_vals.ndim == 3 and shap_vals.shape[-1] == 2:
            # Shape (n_samples, n_features, 2) for binary
            shap_vec = shap_vals[0, :, 1]  # for class 1
        elif isinstance(shap_vals, list) or shap_vals.ndim == 2:
            # List of arrays or 2D array
            shap_vec = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
        else:
            raise ValueError(f"Unexpected SHAP values shape: {shap_vals.shape}")
        shap_vec = np.asarray(shap_vec).flatten()  # ensure 1D array
        print(f"shap_vec shape: {shap_vec.shape}")

        def to_scalar(x):
            x = np.asarray(x)
            #print(f"to_scalar input shape: {x.shape}, size: {x.size}, ndim: {x.ndim}")
            if x.ndim == 0:
                return x.item()
            elif x.size == 1:
                return x.flat[0]
            else:
                raise ValueError(f"Cannot convert array of shape {x.shape} to scalar")

        print(f"expected_value: {explainer.expected_value}, type: {type(explainer.expected_value)}")
        base = to_scalar(explainer.expected_value[1] if isinstance(explainer.expected_value, (list, tuple, np.ndarray)) and len(explainer.expected_value) > 1 else explainer.expected_value)
        print(f"base: {base}")
        recon = float(base + to_scalar(shap_vec.sum()))
        pred = int(to_scalar(self.rf.predict(df[self.features])[0]))

        # Build rows with human values
        rows = []
        for j, feat in enumerate(self.features):
            val = row_dict.get(feat, 0)
            shap_val = to_scalar(shap_vec[j])
            rows.append({
                "feature": feat,
                "value": val,
                "shap": shap_val,
                "abs_shap": abs(shap_val)
            })

        # Sort by absolute impact, high → low
        rows.sort(key=lambda r: r["abs_shap"], reverse=True)

        return {
            "base_value": base,
            "prediction": pred,
            "reconstructed": recon,
            "rows": rows,
        }

    def predict_from_features(self, row_dict: Dict[str, Any]) -> float:
        df = self._prepare_inference_df(row_dict)
        proba = self.rf.predict_proba(df[self.features])[0]
        return float(proba[0])  # probability of class 0

    def predict_by_index(self, idx: int) -> int:
        if self.X_full is None or len(self.X_full) == 0:
            raise ValueError("No training data available for index prediction")
        if idx < 0 or idx >= len(self.X_full):
            raise IndexError(f"Index {idx} out of range")
        row = self.X_full.iloc[[idx]]
        return int(self.rf.predict(row[self.features])[0])