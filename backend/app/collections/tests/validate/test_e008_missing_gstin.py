from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_customer, make_dataset
from app.collections.validate.rules import check_e008_missing_gstin


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e008_missing_gstin(dataset, REPORT_DATE))
    assert {r.customer_id for r in rows} == {"C025"}
    assert all(r.rule_code == "E008" and r.severity == "warning" for r in rows)


def test_present_gstin_does_not_fire() -> None:
    customer = make_customer(gstin="09AAAAA0001A1Z5")
    dataset = make_dataset(customers=[customer])
    assert list(check_e008_missing_gstin(dataset, REPORT_DATE)) == []


def test_malformed_but_present_gstin_does_not_fire_e008() -> None:
    """E006's concern, not E008's -- the two rules are mutually exclusive
    per customer (E006 requires a non-null GSTIN first)."""
    customer = make_customer(gstin="INVALIDGSTIN")
    dataset = make_dataset(customers=[customer])
    assert list(check_e008_missing_gstin(dataset, REPORT_DATE)) == []


def test_none_gstin_fires() -> None:
    customer = make_customer(gstin=None)
    dataset = make_dataset(customers=[customer])
    rows = list(check_e008_missing_gstin(dataset, REPORT_DATE))
    assert len(rows) == 1
