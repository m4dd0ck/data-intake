"""Read client exports as text tables.

Everything is loaded as text on purpose: the audit's job is to find out what types the data
really has, so no reader is allowed to guess and silently coerce first.
"""

from datetime import date, datetime, time
from pathlib import Path

import duckdb
from openpyxl import load_workbook

from data_intake.models import RawTable

SUPPORTED = {".csv", ".txt", ".xlsx", ".xlsm"}


class UnsupportedFileError(ValueError):
    """Raised for a file type the audit cannot read."""


def load_folder(folder: Path) -> list[RawTable]:
    """Load every supported file in a folder (not recursive), sorted by name.

    Raises:
        FileNotFoundError: If the folder does not exist or holds no supported files.
    """
    if not folder.is_dir():
        raise FileNotFoundError(f"Not a folder: {folder}")
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED)
    if not files:
        raise FileNotFoundError(f"No CSV or Excel files in {folder}")
    tables: list[RawTable] = []
    for path in files:
        tables.extend(load_file(path))
    return tables


def load_file(path: Path) -> list[RawTable]:
    """One table per CSV, one per non-empty Excel sheet."""
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return [_build_table(path.stem, path, _read_csv(path))]
    if suffix in {".xlsx", ".xlsm"}:
        return _read_workbook(path)
    raise UnsupportedFileError(f"Unsupported file type: {path.name}")


def _read_csv(path: Path) -> list[list[str | None]]:
    # Reason: header=false so title rows and odd headers reach our own header detection.
    with duckdb.connect() as connection:
        relation = connection.execute(
            "select * from read_csv(?, all_varchar = true, header = false, sample_size = -1)",
            [str(path)],
        )
        return [list(row) for row in relation.fetchall()]


def _read_workbook(path: Path) -> list[RawTable]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    tables = []
    try:
        for sheet in workbook.worksheets:
            rows = [[_cell_text(v) for v in row] for row in sheet.iter_rows(values_only=True)]
            if any(any(cell is not None for cell in row) for row in rows):
                name = path.stem if len(workbook.worksheets) == 1 else f"{path.stem}/{sheet.title}"
                tables.append(_build_table(name, path, rows))
    finally:
        workbook.close()
    return tables


def _cell_text(value: object) -> str | None:
    """Excel cell value as the text a person would see, without reformatting numbers."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.isoformat(" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value)
    return text if text != "" else None


def _build_table(name: str, source: Path, rows: list[list[str | None]]) -> RawTable:
    rows = [row for row in rows if any(cell not in (None, "") for cell in row)]
    header_index = 0
    width = max((len(row) for row in rows), default=0)
    header = rows[header_index] if rows else []
    columns, renamed = clean_headers(list(header) + [None] * (width - len(header)))
    body = [list(row) + [None] * (width - len(row)) for row in rows[header_index + 1 :]]
    return RawTable(name, source, columns, body, header_index, renamed)


def clean_headers(header: list[str | None]) -> tuple[list[str], dict[str, str]]:
    """Trim names, name blanks ``unnamed_N`` and suffix repeats; report what changed."""
    columns: list[str] = []
    renamed: dict[str, str] = {}
    seen: dict[str, int] = {}
    for position, raw in enumerate(header, start=1):
        original = "" if raw is None else str(raw)
        name = original.strip() or f"unnamed_{position}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        if name != original:
            renamed[name] = original
        columns.append(name)
    return columns, renamed
