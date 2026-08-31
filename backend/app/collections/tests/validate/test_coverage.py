"""Rule coverage: every rule in RULE_REGISTRY fires at least once on
dataset A (MASTER_PLAN.md Phase 2 done-when criterion), and the registry
covers exactly E001-E014. Iterates the registry rather than hardcoding
rule names, so this test can never drift from the catalogue.
"""

from app.collections.config import settings
from app.collections.contracts import CanonicalDataset
from app.collections.validate import engine


def test_every_rule_fires_at_least_once_on_dataset_a(dataset: CanonicalDataset) -> None:
    grouped = engine.exceptions_by_rule(dataset, settings.REPORT_DATE)
    for code in engine.RULE_REGISTRY:
        assert grouped.get(code), f"{code} never fired on dataset A"


def test_registry_covers_all_fourteen_codes() -> None:
    assert set(engine.RULE_REGISTRY) == {f"E{n:03d}" for n in range(1, 15)}


def test_total_exception_row_count_on_dataset_a(dataset: CanonicalDataset) -> None:
    """17 rows: every rule fires once except E002 and E013, which fire
    twice each (see docs/RULES.md's summary table)."""
    all_rows = engine.run_all_rules(dataset, settings.REPORT_DATE)
    assert len(all_rows) == 17
