from conftest import codes, context

from data_intake.checks import outliers


def test_extreme_value_is_flagged() -> None:
    rows = [[str(20 + i % 10)] for i in range(40)] + [["5000"]]
    finding = outliers.check(context(["amount"], rows))[0]
    assert finding.code == "outliers"
    assert finding.examples == ["5,000"]


def test_negative_amounts_only_for_amount_like_columns() -> None:
    rows = [["10"], ["-4"], ["12"]]
    assert codes(outliers.check(context(["amount"], rows))) == {"negative_amounts"}
    assert outliers.check(context(["temperature"], rows)) == []


def test_future_and_implausible_dates() -> None:
    rows = [["2024-01-05"], ["2025-02-01"], ["1900-01-01"], ["2024-03-01"]]
    assert codes(outliers.check(context(["order_date"], rows))) == {
        "future_dates",
        "implausible_dates",
    }
