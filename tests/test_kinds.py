from datetime import date

import pytest

from data_intake.kinds import analyse_column, is_blank, parse_date, parse_number, value_kind


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("42", "integer"),
        ("1,234.50", "decimal"),
        ("$1,234.50", "currency"),
        ("12.00 €", "currency"),
        ("USD 99", "currency"),
        ("7.5%", "percent"),
        ("2024-03-04", "date_iso"),
        ("2024-03-04 10:15", "datetime"),
        ("3/4/2024", "date_slash"),
        ("04.03.2024", "date_dot"),
        ("Mar 4, 2024", "date_text"),
        ("yes", "boolean"),
        ("ana@shop.com", "email"),
        ("Blue mug", "text"),
    ],
)
def test_value_kind(value: str, kind: str) -> None:
    assert value_kind(value) == kind


@pytest.mark.parametrize("value", [None, "", " ", "N/A", "null", "-", "?"])
def test_blank_like_values(value: str | None) -> None:
    assert is_blank(value)


def test_parse_number_handles_currency_thousands_and_percent() -> None:
    assert parse_number("$1,234.50") == 1234.5
    assert parse_number("-12") == -12
    assert parse_number("7.5%") == pytest.approx(0.075)
    assert parse_number("abc") is None


def test_parse_date_reads_us_order_unless_day_is_first() -> None:
    assert parse_date("3/4/2024") == date(2024, 3, 4)
    assert parse_date("25/4/2024") == date(2024, 4, 25)
    assert parse_date("Mar 4, 2024") == date(2024, 3, 4)
    assert parse_date("2024-02-30") is None


def test_column_kinds() -> None:
    assert analyse_column("order_date", ["2024-01-01", "1/2/2024", "N/A"]).kind == "date"
    assert analyse_column("amount", ["$5.00", "6.50", "7"]).kind == "currency"
    assert analyse_column("order_id", [str(i) for i in range(50)]).kind == "id"
    assert analyse_column("country", ["US", "GB"] * 30).kind == "category"
    column = analyse_column("note", ["x", "N/A", None])
    assert column.blank_tokens == {"N/A": 1}
    assert column.non_blank == 1
