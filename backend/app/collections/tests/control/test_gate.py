from decimal import Decimal

from app.collections.contracts import ExceptionRow
from app.collections.control.gate import THRESHOLD, evaluate_gate


def _row(invoice_id: str | None = None) -> ExceptionRow:
    return ExceptionRow(
        rule_code="E001",
        category="test",
        message="m",
        severity="error",
        invoice_id=invoice_id,
    )


def test_exactly_at_threshold_passes() -> None:
    # 5/100 == 5% exactly -- strict greater-than, so this passes.
    rows = [_row(f"INV-{i}") for i in range(5)]
    result = evaluate_gate(100, rows)
    assert result.status == "PASSED"
    assert result.exception_row_rate == Decimal("0.05")


def test_just_over_threshold_blocks() -> None:
    rows = [_row(f"INV-{i}") for i in range(6)]
    result = evaluate_gate(100, rows)
    assert result.status == "BLOCKED"
    assert result.exception_row_rate == Decimal("0.06")


def test_zero_invoices_never_blocks() -> None:
    result = evaluate_gate(0, [])
    assert result.status == "PASSED"
    assert result.exception_row_rate == Decimal("0")


def test_row_rate_and_distinct_rate_diverge_on_repeat_offenders() -> None:
    """Three exceptions on the same invoice: row rate counts all three,
    distinct rate counts the invoice once -- this is exactly the
    QA_PREP.md Q8 ambiguity the gate resolves by reporting both."""
    rows = [_row("INV-1"), _row("INV-1"), _row("INV-1")]
    result = evaluate_gate(10, rows)
    assert result.exception_count == 3
    assert result.distinct_invoices_affected == 1
    assert result.exception_row_rate == Decimal("0.3")
    assert result.distinct_invoice_rate == Decimal("0.1")


def test_exceptions_without_invoice_id_count_toward_row_rate_not_distinct() -> None:
    rows = [_row(None), _row(None)]
    result = evaluate_gate(10, rows)
    assert result.exception_count == 2
    assert result.distinct_invoices_affected == 0


def test_threshold_constant_is_five_percent() -> None:
    assert THRESHOLD == Decimal("0.05")
