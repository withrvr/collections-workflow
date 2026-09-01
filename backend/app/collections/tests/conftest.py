from pathlib import Path

import pytest

from app.collections.contracts import CanonicalDataset
from app.collections.ingest.loader import load_workbook

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "dataset_a_original.xlsx"


@pytest.fixture(scope="session")
def dataset() -> CanonicalDataset:
    return load_workbook(FIXTURE_PATH)
