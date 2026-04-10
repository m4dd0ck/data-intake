from conftest import codes, context

from data_intake.checks import formats


def test_mixed_date_formats() -> None:
    ctx = context(["order_date"], [["2024-03-04"], ["2024-03-05"], ["3/6/2024"]])
    finding = formats.check(ctx)[0]
    assert finding.code == "mixed_date_formats"
    assert finding.affected_rows == 1
    assert "2 like 2024-03-04, 1 like 03/04/2024" in finding.detail


def test_currency_text_and_mixed_currencies() -> None:
    ctx = context(["price"], [["$10.00"], ["€12.50"], ["$1,200.00"], ["9.99"]])
    assert codes(formats.check(ctx)) == {"numbers_as_text", "mixed_currencies"}


def test_text_inside_a_number_column() -> None:
    ctx = context(["amount"], [[str(i)] for i in range(20)] + [["TBD"]])
    finding = next(f for f in formats.check(ctx) if f.code == "non_numeric_values")
    assert finding.examples == ["TBD"]


def test_excel_serial_dates() -> None:
    ctx = context(["issued"], [["45412"], ["45413"], ["45420"]])
    assert "excel_serial_dates" in codes(formats.check(ctx))


def test_labels_differing_by_case_or_space() -> None:
    ctx = context(["country"], [["US"], ["us "], ["GB"], ["US"]] * 10)
    assert codes(formats.check(ctx)) == {"inconsistent_labels", "stray_whitespace"}


def test_clean_columns_raise_nothing() -> None:
    ctx = context(
        ["order_date", "amount", "country"],
        [["2024-03-04", "10.50", "US"], ["2024-03-05", "8.00", "GB"]] * 10,
    )
    assert formats.check(ctx) == []
