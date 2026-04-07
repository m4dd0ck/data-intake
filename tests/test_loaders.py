from pathlib import Path

import pytest
from openpyxl import Workbook

from data_intake.loaders import clean_headers, find_header_row, load_folder


def test_title_rows_above_the_header_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "orders.csv").write_text(
        "Order export,,\nGenerated 2024-05-01,,\norder_id,amount,status\n1,10,paid\n"
    )
    table = load_folder(tmp_path)[0]
    assert table.header_row == 2
    assert table.columns == ["order_id", "amount", "status"]
    assert table.rows == [["1", "10", "paid"]]


def test_excel_sheets_load_separately_with_dates_as_iso(tmp_path: Path) -> None:
    from datetime import datetime

    workbook = Workbook()
    first = workbook.active
    assert first is not None
    first.title = "2025"
    first.append(["Invoices", None])
    first.append(["invoice_id", "issued"])
    first.append(["A-1", datetime(2025, 3, 4)])
    second = workbook.create_sheet("2026")
    second.append(["invoice_id", "issued"])
    second.append(["B-1", 46000])
    workbook.save(tmp_path / "invoices.xlsx")

    tables = load_folder(tmp_path)
    assert [t.name for t in tables] == ["invoices/2025", "invoices/2026"]
    assert tables[0].rows == [["A-1", "2025-03-04"]]
    assert tables[1].rows == [["B-1", "46000"]]


def test_blank_and_repeated_headers_are_renamed() -> None:
    columns, renamed = clean_headers(["id", " name ", None, "id"])
    assert columns == ["id", "name", "unnamed_3", "id_2"]
    assert renamed == {"name": " name ", "unnamed_3": "", "id_2": "id"}


def test_header_defaults_to_first_row_when_every_row_is_full() -> None:
    assert find_header_row([["a", "b"], ["1", "2"]]) == 0


def test_empty_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No CSV or Excel"):
        load_folder(tmp_path)
