from pathlib import Path

from conftest import AS_OF, codes

from data_intake.checks import TableContext, structure
from data_intake.models import RawTable


def test_title_rows_renamed_headers_and_empty_columns() -> None:
    table = RawTable(
        "customers",
        Path("customers.xlsx"),
        ["name", "unnamed_2", "name_2"],
        [["Ana", None, "x"], ["Bo", None, "y"]],
        header_row=2,
        renamed_columns={"unnamed_2": "", "name_2": "name"},
    )
    found = structure.check(TableContext.build(table, AS_OF))
    assert codes(found) == {"title_rows", "bad_headers", "empty_columns"}


def test_clean_table_has_no_structure_findings() -> None:
    table = RawTable("t", Path("t.csv"), ["a", "b"], [["1", "2"]])
    assert structure.check(TableContext.build(table, AS_OF)) == []
