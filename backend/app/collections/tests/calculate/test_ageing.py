from datetime import date
from decimal import Decimal

from app.collections.calculate.ageing import (
    BUCKET_0_30,
    BUCKET_31_60,
    BUCKET_61_90,
    BUCKET_90_PLUS,
    ageing_bucket,
    summarize_ageing,
)
from app.collections.calculate.overdue import InvoicePosition
from app.collections.contracts import CanonicalInvoice


def _position(days_overdue: int, outstanding: str = "100") -> InvoicePosition:
    invoice = CanonicalInvoice(
        invoice_id=f"INV-{days_overdue}",
        customer_id="C1",
        invoice_date=date(2026, 1, 1),
        due_date=date(2026, 1, 1),
        invoice_amount=Decimal(outstanding),
        tax_amount=Decimal("0"),
        status="Approved",
        salesperson=None,
        source_system_ref=None,
    )
    return InvoicePosition(
        invoice=invoice, outstanding=Decimal(outstanding), is_overdue=True, days_overdue=days_overdue
    )


def test_bucket_edges() -> None:
    assert ageing_bucket(30) == BUCKET_0_30
    assert ageing_bucket(31) == BUCKET_31_60
    assert ageing_bucket(60) == BUCKET_31_60
    assert ageing_bucket(61) == BUCKET_61_90
    assert ageing_bucket(90) == BUCKET_61_90
    assert ageing_bucket(91) == BUCKET_90_PLUS


def test_summarize_ageing_groups_by_bucket() -> None:
    positions = [_position(10, "100"), _position(45, "200"), _position(95, "50")]
    totals = summarize_ageing(positions)
    assert totals[BUCKET_0_30] == Decimal("100")
    assert totals[BUCKET_31_60] == Decimal("200")
    assert totals[BUCKET_90_PLUS] == Decimal("50")
    assert totals[BUCKET_61_90] == Decimal("0")


def test_summarize_ageing_ignores_non_overdue_positions() -> None:
    current = InvoicePosition(
        invoice=CanonicalInvoice(
            invoice_id="INV-X", customer_id="C1", invoice_date=date(2026, 1, 1), due_date=date(2026, 1, 1),
            invoice_amount=Decimal("100"), tax_amount=Decimal("0"), status="Approved", salesperson=None,
            source_system_ref=None,
        ),
        outstanding=Decimal("0"),
        is_overdue=False,
        days_overdue=0,
    )
    totals = summarize_ageing([current])
    assert sum(totals.values()) == Decimal("0")
