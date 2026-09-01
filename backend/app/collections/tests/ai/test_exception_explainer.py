import re
from pathlib import Path

import pytest

from app.collections.ai.roles.exception_explainer import (
    RULE_METADATA,
    _cached_explanation,
    explain_rules,
)
from app.collections.config import settings
from app.collections.contracts import ExceptionRow
from app.collections.ingest.loader import load_workbook
from app.collections.tests.ai.conftest import requires_ollama
from app.collections.validate.engine import run_all_rules

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_a_original.xlsx"
)
_ID_RE = re.compile(r"\b(?:INV|PAY|C)-?\d{2,6}\b")


def _dataset_a_exception_rows() -> list[ExceptionRow]:
    dataset = load_workbook(FIXTURE_PATH)
    return run_all_rules(dataset, settings.REPORT_DATE)


def test_every_fired_rule_gets_an_explanation() -> None:
    rows = _dataset_a_exception_rows()
    explanations = explain_rules(rows)
    fired_codes = {row.rule_code for row in rows}
    assert set(explanations.keys()) == fired_codes
    assert fired_codes == set(RULE_METADATA.keys())  # all 14 fire on dataset A


def test_auto_fixable_is_always_false() -> None:
    rows = _dataset_a_exception_rows()
    explanations = explain_rules(rows)
    assert all(e.auto_fixable is False for e in explanations.values())


def test_fallback_explanation_uses_rule_metadata_when_ollama_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "OLLAMA_API_BASE", "http://127.0.0.1:1")
    _cached_explanation.cache_clear()
    rows = _dataset_a_exception_rows()
    explanations = explain_rules(rows)
    e001 = explanations["E001"]
    assert e001.source == "fallback"
    assert e001.cause == RULE_METADATA["E001"]["cause"]
    _cached_explanation.cache_clear()


@requires_ollama
def test_explanation_never_invents_an_id_not_in_its_batch() -> None:
    _cached_explanation.cache_clear()
    rows = _dataset_a_exception_rows()
    explanations = explain_rules(rows)
    for rule_code, explanation in explanations.items():
        rule_rows = [r for r in rows if r.rule_code == rule_code]
        allowed: set[str] = set()
        for row in rule_rows:
            for id_ in (row.invoice_id, row.payment_id, row.customer_id):
                if id_:
                    allowed.add(id_.upper())
        mentioned = {m.group().upper() for m in _ID_RE.finditer(explanation.cause)}
        assert mentioned <= allowed, (
            f"{rule_code} explanation invented an ID: {mentioned - allowed}"
        )
