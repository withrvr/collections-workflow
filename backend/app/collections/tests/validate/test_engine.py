from datetime import date

from app.collections.contracts import CanonicalDataset
from app.collections.validate import engine

REPORT_DATE = date(2026, 7, 31)


def test_run_all_rules_returns_empty_list_for_empty_dataset() -> None:
    empty = CanonicalDataset(customers=[], invoices=[], payments=[], region_map=[])
    assert engine.run_all_rules(empty, REPORT_DATE) == []


def test_exceptions_by_rule_has_no_findings_for_empty_dataset() -> None:
    """Registry-size-agnostic: however many rules are registered, none of
    them should find anything to flag in a dataset with no rows at all."""
    empty = CanonicalDataset(customers=[], invoices=[], payments=[], region_map=[])
    grouped = engine.exceptions_by_rule(empty, REPORT_DATE)
    assert set(grouped) == set(engine.RULE_REGISTRY)
    assert all(rows == [] for rows in grouped.values())
