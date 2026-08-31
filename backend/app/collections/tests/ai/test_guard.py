from app.collections.ai.guard import numbers_are_contained


def test_matching_numbers_pass() -> None:
    context = "36 invoices, 15 overdue, Rs 1,202,000.00 outstanding."
    output = "Of the 36 invoices, 15 are overdue totaling Rs 1202000.00."
    assert numbers_are_contained(output, context)


def test_invented_number_fails() -> None:
    context = "36 invoices, 15 overdue."
    output = "Of the 36 invoices, 22 are overdue."  # 22 was never given
    assert not numbers_are_contained(output, context)


def test_no_numbers_in_output_always_passes() -> None:
    assert numbers_are_contained("Everything looks fine.", "36 invoices")


def test_date_hyphen_is_not_treated_as_a_negative_sign() -> None:
    context = "Report date: 2026-07-31"
    output = "As of 31 July 2026."
    assert numbers_are_contained(output, context)


def test_percent_and_currency_symbols_do_not_affect_matching() -> None:
    context = "Exception rate: 47.2%. Total: Rs 1,202,000.00."
    output = "The rate was 47.2 percent on a total of 1202000.00."
    assert numbers_are_contained(output, context)
