from conftest import codes, context

from data_intake.checks import duplicates


def test_exact_duplicate_rows_are_counted() -> None:
    ctx = context(["order_id", "amount"], [["1", "5"], ["1", "5"], ["2", "7"], ["1", "5 "]])
    finding = next(f for f in duplicates.check(ctx) if f.code == "duplicate_rows")
    assert finding.affected_rows == 2  # trailing space does not make a row different


def test_conflicting_keys_are_critical_but_plain_copies_are_not() -> None:
    rows = [[str(i), "10"] for i in range(40)] + [["3", "10"], ["7", "99"]]
    found = duplicates.check(context(["order_id", "amount"], rows))
    assert codes(found) == {"duplicate_rows", "duplicate_keys"}
    key_finding = next(f for f in found if f.code == "duplicate_keys")
    assert key_finding.examples == ["7"]  # "3" only repeats as an exact copy
    assert key_finding.severity == "critical"


def test_foreign_keys_that_repeat_by_design_are_ignored() -> None:
    rows = [[str(i), f"C{i % 5}"] for i in range(50)]
    assert duplicates.check(context(["order_id", "customer_id"], rows)) == []


def test_email_case_variants_and_similar_names() -> None:
    ctx = context(
        ["customer_name", "email"],
        [
            ["Harbor Supply Co", "ops@harbor.com"],
            ["Harbour Supply Co", "OPS@harbor.com"],
            ["Maple Studio", "hi@maple.io"],
        ],
    )
    found = [f for f in duplicates.check(ctx) if f.code == "near_duplicate_records"]
    assert {f.column for f in found} == {"customer_name", "email"}
