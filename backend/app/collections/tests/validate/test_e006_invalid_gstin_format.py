from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_customer, make_dataset
from app.collections.validate.rules import check_e006_invalid_gstin_format


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e006_invalid_gstin_format(dataset, REPORT_DATE))
    assert {r.customer_id for r in rows} == {"C023"}
    assert all(r.rule_code == "E006" and r.severity == "warning" for r in rows)


def test_well_formed_gstin_does_not_fire() -> None:
    customer = make_customer(gstin="09AAAAA0001A1Z5")
    dataset = make_dataset(customers=[customer])
    assert list(check_e006_invalid_gstin_format(dataset, REPORT_DATE)) == []


def test_missing_gstin_does_not_fire_e006() -> None:
    """None is E008's concern, not E006's -- the two rules are mutually
    exclusive per customer."""
    customer = make_customer(gstin=None)
    dataset = make_dataset(customers=[customer])
    assert list(check_e006_invalid_gstin_format(dataset, REPORT_DATE)) == []


def test_malformed_gstin_fires() -> None:
    customer = make_customer(gstin="INVALIDGSTIN")
    dataset = make_dataset(customers=[customer])
    rows = list(check_e006_invalid_gstin_format(dataset, REPORT_DATE))
    assert len(rows) == 1
    assert rows[0].detail["gstin"] == "INVALIDGSTIN"
