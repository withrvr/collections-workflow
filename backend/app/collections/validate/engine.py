"""Runs all registered rules against a loaded workbook and emits ExceptionRow[].

RULE_REGISTRY is built up incrementally, one entry per rule, in the same
commit as the rule function itself (see validate/rules.py). This is what
lets tests/validate/test_coverage.py iterate the registry instead of
hardcoding rule names -- the coverage test can never drift from the
catalogue because it never names a rule directly.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date

from app.collections.contracts import CanonicalDataset, ExceptionRow
from app.collections.validate import rules

RuleFn = Callable[[CanonicalDataset, date], Iterator[ExceptionRow]]

RULE_REGISTRY: dict[str, RuleFn] = {
    "E001": rules.check_e001_missing_due_date,
    "E004": rules.check_e004_non_positive_invoice_amount,
    "E011": rules.check_e011_cancelled_invoice,
    "E012": rules.check_e012_credit_note_invoice,
    "E013": rules.check_e013_duplicate_source_system_ref,
    "E006": rules.check_e006_invalid_gstin_format,
    "E008": rules.check_e008_missing_gstin,
    "E005": rules.check_e005_non_positive_payment_amount,
    "E009": rules.check_e009_payment_after_report_date,
    "E002": rules.check_e002_unknown_customer_reference,
}


def run_all_rules(dataset: CanonicalDataset, report_date: date) -> list[ExceptionRow]:
    return [row for rule_fn in RULE_REGISTRY.values() for row in rule_fn(dataset, report_date)]


def exceptions_by_rule(dataset: CanonicalDataset, report_date: date) -> dict[str, list[ExceptionRow]]:
    """Grouped view, keyed by rule code -- used by the coverage test and,
    later, control/gate.py and the exceptions API filter."""
    grouped: dict[str, list[ExceptionRow]] = {code: [] for code in RULE_REGISTRY}
    for row in run_all_rules(dataset, report_date):
        grouped.setdefault(row.rule_code, []).append(row)
    return grouped
