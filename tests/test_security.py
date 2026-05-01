"""Hostile or accidental inputs: giant sheet dimensions, symlinks, glob names, unsafe --out."""

import re
import zipfile
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

from data_intake.audit import run_audit
from data_intake.loaders import load_folder
from data_intake.report import render_html, without_examples
from data_intake.site import SITE_MARKER, UnsafeOutputError, _clear_previous_site

HUGE = b'<dimension ref="A1:XFD1048576"/>'


def test_sheet_claiming_a_huge_size_loads_only_real_cells(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["id", "value"])
    sheet.append(["1", "a"])
    small = tmp_path / "small.xlsx"
    workbook.save(small)
    # Rewrite the sheet XML to declare the largest possible range, as a hostile file could.
    hostile = tmp_path / "exports" / "hostile.xlsx"
    hostile.parent.mkdir()
    with zipfile.ZipFile(small) as source, zipfile.ZipFile(hostile, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data, replaced = re.subn(rb"<dimension ref=\"[^\"]+\"\s*/>", HUGE, data)
                assert replaced == 1
            target.writestr(item, data)
    table = load_folder(hostile.parent)[0]
    assert table.columns == ["id", "value"]
    assert table.rows == [["1", "a"]]


def test_symlinked_files_are_not_read(tmp_path: Path) -> None:
    secret = tmp_path / "secret.csv"
    secret.write_text("token\nabc123\n")
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "orders.csv").write_text("id\n1\n")
    (exports / "link.csv").symlink_to(secret)
    assert [t.name for t in load_folder(exports)] == ["orders"]


def test_file_name_with_glob_characters_is_read_on_its_own(tmp_path: Path) -> None:
    (tmp_path / "Sales [2024].csv").write_text("id\n1\n")
    (tmp_path / "other.csv").write_text("id\n2\n3\n")
    tables = {t.name: t for t in load_folder(tmp_path)}
    assert tables["Sales [2024]"].rows == [["1"]]


def test_site_refuses_to_delete_a_folder_it_did_not_build(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("important")
    with pytest.raises(UnsafeOutputError):
        _clear_previous_site(tmp_path)
    assert (tmp_path / "keep.txt").exists()
    built = tmp_path / "site"
    built.mkdir()
    (built / SITE_MARKER).write_text("")
    _clear_previous_site(built)
    assert not built.exists()


def test_hidden_examples_keep_findings_but_drop_values(tmp_path: Path) -> None:
    (tmp_path / "people.csv").write_text("email\nana@x.com\nANA@x.com\n")
    audit = without_examples(run_audit(tmp_path, "Co", as_of=date(2024, 1, 1)))
    assert audit.findings and all(f.examples == [] for f in audit.findings)
    assert "ana@x.com" not in render_html(audit).lower()
