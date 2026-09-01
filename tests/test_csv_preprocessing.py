# import pandas as pd

# from src.backend.ai_model import AIModel


# def test_single_test_csv_row_processes_without_string_numeric_error():
#     row = pd.read_csv(r'd:\LTID\credit-scoring-app\test_data\SingleTest.csv').iloc[0].to_dict()

#     data = pd.DataFrame([row])
#     processed = AIModel.process_data(data)

#     assert 'Target' in processed.columns
#     assert processed['Amount Finance'].dtype.kind in {'i', 'f'}
#     assert processed['Mode of Payment'].dtype == object


# import pyodbc

# print(pyodbc.drivers())