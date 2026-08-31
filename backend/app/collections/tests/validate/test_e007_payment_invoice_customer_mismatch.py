from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice, make_payment
from app.collections.validate.rules import check_e007_payment_invoice_customer_mismatch


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    """The flagship worked example (MASTER_PLAN.md section 8, QA_PREP.md Q11):
    PAY-2026 pays INV-1002 under C003, but INV-1002 belongs to C002."""
    rows = list(check_e007_payment_invoice_customer_mismatch(dataset, REPORT_DATE))
    assert {r.payment_id for r in rows} == {"PAY-2026"}
    row = rows[0]
    assert row.rule_code == "E007"
    assert row.severity == "error"
    assert row.invoice_id == "INV-1002"
    assert row.customer_id == "C003"
    assert row.detail["payment_customer_id"] == "C003"
    assert row.detail["invoice_customer_id"] == "C002"


def test_same_customer_payment_does_not_fire() -> None:
    invoice = make_invoice(invoice_id="INV-1", customer_id="C002")
    payment = make_payment(invoice_id="INV-1", customer_id="C002")
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e007_payment_invoice_customer_mismatch(dataset, REPORT_DATE)) == []


def test_mismatched_customer_payment_fires() -> None:
    invoice = make_invoice(invoice_id="INV-1", customer_id="C002")
    payment = make_payment(invoice_id="INV-1", customer_id="C003")
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    rows = list(check_e007_payment_invoice_customer_mismatch(dataset, REPORT_DATE))
    assert len(rows) == 1


def test_unresolved_invoice_reference_does_not_fire_e007() -> None:
    """E003's concern, not E007's -- comparing against nothing would be a
    spurious secondary flag on an already-broken reference."""
    payment = make_payment(invoice_id="INV-9999", customer_id="C999")
    dataset = make_dataset(invoices=[], payments=[payment])
    assert list(check_e007_payment_invoice_customer_mismatch(dataset, REPORT_DATE)) == []
