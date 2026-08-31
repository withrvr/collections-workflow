from datetime import date

from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_payment
from app.collections.validate.rules import check_e009_payment_after_report_date


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e009_payment_after_report_date(dataset, REPORT_DATE))
    assert {r.payment_id for r in rows} == {"PAY-2020"}
    assert all(r.rule_code == "E009" and r.severity == "warning" for r in rows)


def test_payment_after_report_date_fires() -> None:
    dataset = make_dataset(payments=[make_payment(payment_date=date(2026, 8, 1))])
    assert len(list(check_e009_payment_after_report_date(dataset, REPORT_DATE))) == 1


def test_payment_on_report_date_does_not_fire() -> None:
    dataset = make_dataset(payments=[make_payment(payment_date=REPORT_DATE)])
    assert list(check_e009_payment_after_report_date(dataset, REPORT_DATE)) == []


def test_payment_before_report_date_does_not_fire() -> None:
    dataset = make_dataset(payments=[make_payment(payment_date=date(2026, 6, 1))])
    assert list(check_e009_payment_after_report_date(dataset, REPORT_DATE)) == []
