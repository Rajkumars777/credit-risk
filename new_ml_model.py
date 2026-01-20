import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import curve_fit
from google.colab import files
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, confusion_matrix,
                              classification_report)
from sklearn.preprocessing import LabelEncoder

"""
--------------------
Upload and Load Data
--------------------
"""
try:
  original_data = pd.read_excel('/content/20250204Variables 002 - Final01.xlsx')
except:
  uploaded = files.upload()
  filename = list(uploaded.keys())[0]
  original_data = pd.read_excel(filename)

# Work on a copy of the original data for processing:
data = original_data.copy()

n_original = data.shape[0]
print("Number of records originally loaded:", n_original)



"""
----------------------------
Transforming Target Variable
----------------------------
"""
# Funtion to bin 'Longest DPD'
def quantize_longest_dpd(x):
    if x <= 30:
        return 0 # 0 to 30
    else:
        return 1 # 31 and more

data['Original Longest DPD'] = data['Longest DPD']
data['Longest DPD'] = data['Longest DPD'].apply(quantize_longest_dpd)


"""
---------------------------
Defining Target and Features
---------------------------
"""
target = 'Longest DPD'
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
    'DSCR - %', #Debt Service Coverage Ratio
    'Home Ownership - TYPE',
    'Residence Tenure  - Scoring Code',
    'Citizenship  - type',
    'Type of dealer  - Scoring Code',
    'Submitted ID   - type',
    'Marital Status - Scoring Code',
    'Product Type',
    'Contract Start Date',
    'Vehicle List Price',
    'LOAN AMORT',
    'Mode of Payment',
    'Co-Borrowers',
    'Age',
    'LRD'
]

categorical_cols = [
    'Employment Type  - type',
    'Home Ownership - TYPE',
    'Citizenship  - type',
    'Submitted ID   - type',
    'Product Type',
    'Mode of Payment',
    'Co-Borrowers',
    'LRD'
]

"""
------------------
Proprocessing Data
------------------
"""
data['Contract Start Date'] = pd.to_datetime(data['Contract Start Date'], format='%m/%d/%Y', errors='coerce')

# Handling SOA error -->
data['Contract Start Date'].fillna(pd.Timestamp(0), inplace=True)
data['Contract Start Date'] = data['Contract Start Date'].astype(int) / 10**9

for col in categorical_cols:
  if col not in features:
    features.append(col)

numerical_cols = []
for col in features:
  if col not in categorical_cols:
    numerical_cols.append(col)
    data[col] = pd.to_numeric(data[col], errors='coerce')
    data[col].fillna(0, inplace=True)

"""
-----------------------
EDA & Outlier Detection
-----------------------
"""
outlier_analysis_results = {}

for col in numerical_cols:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
    num_outliers = len(outliers)
    percentage_outliers = (num_outliers / len(df)) * 100
    remaining_rows = len(df) - num_outliers

    outlier_analysis_results[col] = {
        'Q1': Q1,
        'Q3': Q3,
        'IQR': IQR,
        'Lower Bound': lower_bound,
        'Upper Bound': upper_bound,
        'Number of Outliers': num_outliers,
        'Percentage of Outliers': percentage_outliers,
        'Remaining Rows (if trimmed)': remaining_rows
    }

print("Outlier Detection and Trimming Analysis Summary:")
print("--------------------------------------------------")
for col, results in outlier_analysis_results.items():
    print(f"\nColumn: {col}")
    for key, value in results.items():
        if 'Percentage' in key:
            print(f"  {key}: {value:.2f}%")
        elif 'Number' in key or 'Remaining' in key:
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value:.2f}")
    if results['Number of Outliers'] > 0:
        print(f"  Potential impact on dataset size if trimmed: {results['Number of Outliers']} rows would be removed, leaving {results['Remaining Rows (if trimmed)']}/{len(df)} rows ({results['Remaining Rows (if trimmed)']/len(df)*100:.2f}%).")
    else:
        print("  No outliers detected by IQR method for this column.")

# above_zero_only = ['Age', 'Vehicle List Price', 'Amount Financed - Amount']
# for col in above_zero_only:
#   data[col] = data[col]>0

data.drop_duplicates(inplace=True)

"""
-----------------
One Hot Encodding
-----------------
"""
# data.replace([np.inf, -np.inf], np.nan, inplace=True)
# onehot_transf = pd.get_dummies(data[categorical_cols]).astype('int')
# df = pd.concat([data[numerical_cols], onehot_transf, data[target]], axis=1)
# onehot_transf = pd.get_dummies(data=data).astype('int')
# df = onehot_transf

"""
--------------
Label Encoding
--------------
"""
le_dict = {}
for col in categorical_cols:
    le = LabelEncoder()
    data[col] = le.fit_transform(data[col].astype(str))
    le_dict[col] = le
    print(f"{col} mapping:", dict(zip(le.classes_, range(len(le.classes_)))))

df = data[numerical_cols + categorical_cols + [target]].copy()
df = df.astype('int')

# Sample Skewness Understanding
print("Db size with Target value = 0 :", df[df[target] == 0].shape)
print("Db size with Target value != 0 :", df[df[target] != 0].shape)


"""
-------------------
Additional Features
-------------------
"""
# # Financial ratios
# df['Downpayment_Ratio'] = df['Downpayment - Amount'] / (df['Amount Financed - Amount'] + 1)
# df['Payment_to_Income'] = df['LOAN AMORT'] / (df['INCOME - Amount'] + 1)
# df['Loan_to_Value'] = df['Amount Financed - Amount'] / (df['Vehicle List Price'] + 1)
# df['Debt_Service_Ratio'] = df['DSCR - %'] / 100  # If not already normalized

# # Contract date features (if Contract Start Date is datetime)
# df['Contract_Year'] = pd.to_datetime(df['Contract Start Date'], unit='s').dt.year
# df['Contract_Month'] = pd.to_datetime(df['Contract Start Date'], unit='s').dt.month
# df['Contract_Quarter'] = pd.to_datetime(df['Contract Start Date'], unit='s').dt.quarter

# # Age groups (bin continuous age)
# df['Age_Group'] = pd.cut(df['Age'], bins=[0, 25, 35, 45, 55, 100], labels=[1, 2, 3, 4, 5])

# new_features = ['Downpayment_Ratio', 'Payment_to_Income', 'Loan_to_Value', 'Contract_Year', 'Contract_Month', 'Age_Group']
# features.extend(new_features)


"""
---------------
Banced Data Set
---------------
"""
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

df_balanced = make_balanced_dataset(df, target, 4)

print("After balance db Target value = 0 :", df_balanced[df_balanced[target] == 0].shape)
print("After balance db Target value != 0 :", df_balanced[df_balanced[target] != 0].shape)

x = df_balanced.drop(target, axis=1)
y = df_balanced[target]

x_train , x_test , y_train , y_test = train_test_split(x, y, test_size=0.3, random_state=42)

rf = RandomForestClassifier(n_estimators=300,
                            random_state=2,
                            n_jobs=-1,
                            max_depth=25)
rf.fit(x_train, y_train)
y_pred = rf.predict(x_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print("F1 Score:", f1_score(y_test, y_pred, average='weighted'))