"""The demo exports are the answer key: every planted problem must be found, and columns
known to be clean must produce nothing."""

from pathlib import Path

import pytest

from data_intake.audit import run_audit
from data_intake.demo import AS_OF, CLEAN_COLUMNS, PLANTED, build_demo
from data_intake.models import Audit


@pytest.fixture(scope="module")
def audits(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Audit]:
    folders = build_demo(tmp_path_factory.mktemp("demo"))
    return {name: run_audit(folder, name, as_of=AS_OF) for name, folder in folders.items()}


@pytest.mark.parametrize("planted", PLANTED, ids=lambda p: f"{p.table}:{p.code}:{p.column}")
def test_every_planted_issue_is_found(audits: dict[str, Audit], planted: object) -> None:
    found = {(f.table, f.code, f.column) for f in audits[planted.business].findings}  # type: ignore[attr-defined]
    assert (planted.table, planted.code, planted.column) in found  # type: ignore[attr-defined]


@pytest.mark.parametrize("business,table,column", CLEAN_COLUMNS)
def test_clean_columns_raise_nothing(
    audits: dict[str, Audit], business: str, table: str, column: str
) -> None:
    noisy = [f.code for f in audits[business].findings if f.table == table and f.column == column]
    assert noisy == []


def test_demo_is_deterministic(tmp_path: Path) -> None:
    first = build_demo(tmp_path / "a")
    second = build_demo(tmp_path / "b")
    for name in first:
        for path in sorted(first[name].iterdir()):
            if path.suffix == ".csv":
                assert path.read_bytes() == (second[name] / path.name).read_bytes()
