from decimal import Decimal

from app.collections.ai.fallback import render_summary
from app.collections.contracts import ExceptionRow
from app.collections.control.gate import evaluate_gate


def test_render_summary_blocked_mentions_threshold_and_status() -> None:
    rows = [
        ExceptionRow(
            rule_code="E001",
            category="c",
            message="m",
            severity="error",
            invoice_id=f"INV-{i}",
        )
        for i in range(17)
    ]
    gate = evaluate_gate(36, rows)
    text = render_summary(
        source_filename="dataset_a_original.xlsx",
        report_date="2026-07-31",
        customer_count=25,
        invoice_count=36,
        overdue_count=15,
        total_outstanding=Decimal("1202000.00"),
        heaviest_region="West",
        by_region={"West": Decimal("472000.00"), "East": Decimal("293000.00")},
        ageing={"0-30": Decimal("100000.00"), "31-60": Decimal("50000.00")},
        rule_counts={"E001": 17},
        gate=gate,
    )
    assert "BLOCKED" in text
    assert "5%" in text or "5.0%" in text
    assert "West" in text
    assert "1,202,000.00" in text
    assert "E001" in text  # top rules called out by name
    assert "0-30" in text  # ageing breakdown surfaced


def test_render_summary_passed_mentions_status() -> None:
    gate = evaluate_gate(19, [])
    text = render_summary(
        source_filename="dataset_b_clean.xlsx",
        report_date="2026-07-31",
        customer_count=15,
        invoice_count=19,
        overdue_count=6,
        total_outstanding=Decimal("347000.00"),
        heaviest_region="East",
        by_region=None,
        ageing=None,
        rule_counts=None,
        gate=gate,
    )
    assert "PASSED" in text
    assert "BLOCKED" not in text


def test_render_summary_handles_no_heaviest_region() -> None:
    gate = evaluate_gate(0, [])
    text = render_summary(
        source_filename="empty.xlsx",
        report_date="2026-07-31",
        customer_count=0,
        invoice_count=0,
        overdue_count=0,
        total_outstanding=Decimal("0"),
        heaviest_region=None,
        by_region=None,
        ageing=None,
        rule_counts=None,
        gate=gate,
    )
    assert "empty.xlsx" in text
