from decimal import Decimal

from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_payment
from app.collections.validate.rules import check_e005_non_positive_payment_amount


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e005_non_positive_payment_amount(dataset, REPORT_DATE))
    assert {r.payment_id for r in rows} == {"PAY-2018", "PAY-2029"}
    assert all(r.rule_code == "E005" and r.severity == "error" for r in rows)


def test_zero_amount_fires() -> None:
    dataset = make_dataset(payments=[make_payment(payment_amount=Decimal("0"))])
    assert len(list(check_e005_non_positive_payment_amount(dataset, REPORT_DATE))) == 1


def test_negative_amount_fires() -> None:
    dataset = make_dataset(payments=[make_payment(payment_amount=Decimal("-1"))])
    assert len(list(check_e005_non_positive_payment_amount(dataset, REPORT_DATE))) == 1


def test_positive_amount_does_not_fire() -> None:
    dataset = make_dataset(payments=[make_payment(payment_amount=Decimal("100"))])
    assert list(check_e005_non_positive_payment_amount(dataset, REPORT_DATE)) == []
