from conftest import codes, context

from data_intake.checks import missing


def test_placeholders_are_reported_with_examples() -> None:
    ctx = context(["customer_id"], [["C1"], ["N/A"], ["-"], ["C2"], ["C3"], ["C4"]])
    finding = next(f for f in missing.check(ctx) if f.code == "blank_placeholders")
    assert finding.affected_rows == 2
    assert finding.examples == ["N/A", "-"]


def test_mostly_filled_columns_are_not_flagged() -> None:
    ctx = context(["city"], [["Leeds"]] * 9 + [[None]])
    assert codes(missing.check(ctx)) == set()


def test_high_missing_share_is_flagged() -> None:
    ctx = context(["phone"], [["1"], [None], [None], ["2"]])
    assert codes(missing.check(ctx)) == {"high_missing"}
