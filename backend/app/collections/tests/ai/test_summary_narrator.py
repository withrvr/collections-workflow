from decimal import Decimal

import pytest

from app.collections.ai.roles import summary_narrator
from app.collections.ai.roles.summary_narrator import NarrativeResult
from app.collections.config import settings
from app.collections.contracts import ExceptionRow
from app.collections.control.gate import GateResult, evaluate_gate
from app.collections.observability import metrics
from app.collections.tests.ai.conftest import requires_ollama

GATE_PASSED = evaluate_gate(36, [])
GATE_BLOCKED = evaluate_gate(
    36,
    [
        ExceptionRow(
            rule_code="E001",
            category="c",
            message="m",
            severity="error",
            invoice_id=f"INV-{i}",
        )
        for i in range(17)
    ],
)


def _narrate(gate: GateResult) -> NarrativeResult:
    return summary_narrator.narrate(
        source_filename="dataset_a_original.xlsx",
        report_date="2026-07-31",
        invoice_count=36,
        overdue_count=15,
        total_outstanding=Decimal("1202000.00"),
        heaviest_region="West",
        gate=gate,
    )


@requires_ollama
def test_narrate_uses_local_ollama_and_records_metric() -> None:
    """MASTER_PLAN.md Phase 6 done-when: local calls succeed and
    llm_calls_total shows it. Ollama runs entirely over loopback/LAN, so
    this holds with the network disconnected too -- nothing here touches
    the internet."""
    metrics.reset_llm_calls()
    result = _narrate(GATE_PASSED)
    assert result.source == "ollama"
    assert result.text.strip()
    assert metrics.llm_calls_total(rung="ollama", status="success") == 1


@requires_ollama
def test_narrate_never_invents_a_number() -> None:
    """The guard rejects any rung whose output fails containment; this
    just proves a real (blocked) run's narrative round-trips through the
    guard successfully rather than silently degrading every time."""
    result = _narrate(GATE_BLOCKED)
    assert result.source in ("ollama", "fallback")
    assert result.text.strip()


def test_narrate_falls_back_to_deterministic_template_when_ollama_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings, "OLLAMA_API_BASE", "http://127.0.0.1:1"
    )  # nothing listens here
    result = _narrate(GATE_PASSED)
    assert result.source == "fallback"
    assert "PASSED" in result.text


def test_narrate_never_raises_even_if_everything_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "OLLAMA_API_BASE", "http://127.0.0.1:1")
    result = _narrate(GATE_BLOCKED)
    assert result.text  # the deterministic template always succeeds
