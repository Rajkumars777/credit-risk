"""Unit tests for CSV preprocessing with sample test datasets."""

from pathlib import Path
import pytest

from src.backend.ai_model import AIModel
from src.frontend.main import read_csv_safe

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def test_single_test_csv_row_processes_without_error():
    """Verify single-row CSV from test_data is correctly processed by AIModel."""
    csv_file = TEST_DATA_DIR / "SingleTest.csv"
    assert csv_file.exists(), f"Missing fixture file: {csv_file}"

    df = read_csv_safe(str(csv_file))
    processed = AIModel.process_data(df, inference=True)

    assert not processed.empty
    assert processed["Amount Finance"].dtype.kind in {"i", "f"}
    assert "DSCR" in processed.columns


def test_multiple_test_csv_processes_without_error():
    """Verify multi-row batch CSV with tokenization tolerance is correctly loaded and processed."""
    csv_file = TEST_DATA_DIR / "MultipleTest.csv"
    assert csv_file.exists(), f"Missing fixture file: {csv_file}"

    df = read_csv_safe(str(csv_file))
    assert not df.empty
    processed = AIModel.process_data(df, inference=True)

    assert len(processed) == len(df)
    assert processed["Amount Finance"].dtype.kind in {"i", "f"}
