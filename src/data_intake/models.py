"""Data structures shared by the loaders, checks, audit and report."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


@dataclass
class RawTable:
    """One CSV file or Excel sheet as text, after header detection.

    ``rows`` hold cell text (None for empty cells) aligned to ``columns``.
    """

    name: str
    source: Path
    columns: list[str]
    rows: list[list[str | None]]
    header_row: int = 0  # 0-based line/row where the header was found
    renamed_columns: dict[str, str] = field(default_factory=dict)  # new name -> original

    def column_values(self, index: int) -> list[str | None]:
        return [row[index] for row in self.rows]


class Severity(StrEnum):
    CRITICAL = "critical"  # blocks a correct analysis until fixed
    WARNING = "warning"  # needs cleaning; results would be off
    INFO = "info"  # worth knowing, no action needed


SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}


class Finding(BaseModel):
    """One problem, stated for a client: what, where, examples, and what it means."""

    code: str
    severity: Severity
    table: str
    column: str | None = None
    title: str
    detail: str
    impact: str
    examples: list[str] = Field(default_factory=list)
    affected_rows: int | None = None


class ColumnProfile(BaseModel):
    name: str
    kind: str
    non_empty: int
    distinct: int
    examples: list[str]
    minimum: str | None = None
    maximum: str | None = None


class TableProfile(BaseModel):
    name: str
    source: str
    rows: int
    columns: list[ColumnProfile]
    header_row: int


class JoinCandidate(BaseModel):
    """A column pair that looks like a key relationship between two tables."""

    left_table: str
    left_column: str
    right_table: str
    right_column: str
    containment: float  # share of left values found in right
    orphan_values: int  # distinct left values with no match


class KpiSuggestion(BaseModel):
    name: str
    tables: list[str]
    why: str


class Audit(BaseModel):
    client: str
    tables: list[TableProfile]
    findings: list[Finding]
    joins: list[JoinCandidate]
    kpis: list[KpiSuggestion]

    def count(self, severity: Severity) -> int:
        return sum(1 for finding in self.findings if finding.severity == severity)
