from datetime import date
from pathlib import Path

from data_intake.checks import TableContext
from data_intake.models import Finding, RawTable

AS_OF = date(2024, 6, 30)


def context(columns: list[str], rows: list[list[str | None]], name: str = "t") -> TableContext:
    return TableContext.build(RawTable(name, Path(f"{name}.csv"), columns, rows), AS_OF)


def codes(findings: list[Finding]) -> set[str]:
    return {finding.code for finding in findings}
