from datetime import date
from decimal import Decimal

from app.collections.calculate.overdue import compute_positions
from app.collections.contracts import CanonicalCustomer, CanonicalDataset, CanonicalInvoice, CanonicalPayment, RegionMap

REPORT_DATE = date(2026, 7, 31)


def _customer(customer_id: str = "C1") -> CanonicalCustomer:
    return CanonicalCustomer(
        customer_id=customer_id,
        customer_name="Test Customer",
        city="Test City",
        state="Test State",
        region="North",
        gstin="09AAAAA0001A1Z5",
        credit_limit=Decimal("100000"),
        active_flag=True,
    )


def _invoice(**overrides: object) -> CanonicalInvoice:
    defaults: dict[str, object] = dict(
        invoice_id="INV-1",
        customer_id="C1",
        invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30),
        invoice_amount=Decimal("1000"),
        tax_amount=Decimal("180"),
        status="Approved",
        salesperson="Rohit",
        source_system_ref="EMP-SO-1",
    )
    defaults.update(overrides)
    return CanonicalInvoice(**defaults)


def _dataset(invoices: list[CanonicalInvoice], payments: list[CanonicalPayment] | None = None) -> CanonicalDataset:
    return CanonicalDataset(
        customers=[_customer()],
        invoices=invoices,
        payments=payments or [],
        region_map=[RegionMap(state="Test State", region="North")],
    )


def test_due_exactly_on_report_date_is_not_overdue() -> None:
    """The INV-1012 pattern: Due Date is compared strictly less-than."""
    invoice = _invoice(due_date=REPORT_DATE)
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert len(positions) == 1
    assert positions[0].is_overdue is False


def test_payment_exactly_on_report_date_reduces_outstanding() -> None:
    """The PAY-2011/PAY-2012 pattern: payments on the report date count."""
    invoice = _invoice(due_date=date(2026, 7, 1), invoice_amount=Decimal("1000"))
    payment = CanonicalPayment(
        payment_id="PAY-1",
        customer_id="C1",
        invoice_id="INV-1",
        payment_date=REPORT_DATE,
        payment_amount=Decimal("1000"),
        payment_mode="NEFT",
        bank_ref="REF-1",
    )
    positions = compute_positions(_dataset([invoice], [payment]), REPORT_DATE)
    assert positions[0].outstanding == Decimal("0")
    assert positions[0].is_overdue is False


def test_due_before_report_date_with_outstanding_is_overdue() -> None:
    invoice = _invoice(due_date=date(2026, 6, 1), invoice_amount=Decimal("500"))
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions[0].is_overdue is True
    assert positions[0].days_overdue == (REPORT_DATE - date(2026, 6, 1)).days


def test_cancelled_status_excluded() -> None:
    invoice = _invoice(status="Cancelled", due_date=date(2026, 6, 1))
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions == []


def test_credit_note_status_excluded() -> None:
    invoice = _invoice(status="Credit Note", due_date=date(2026, 6, 1))
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions == []


def test_unknown_customer_excluded() -> None:
    invoice = _invoice(customer_id="C999", due_date=date(2026, 6, 1))
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions == []


def test_missing_due_date_excluded() -> None:
    invoice = _invoice(due_date=None)
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions == []


def test_non_positive_invoice_amount_excluded() -> None:
    invoice = _invoice(invoice_amount=Decimal("-100"), due_date=date(2026, 6, 1))
    positions = compute_positions(_dataset([invoice]), REPORT_DATE)
    assert positions == []
