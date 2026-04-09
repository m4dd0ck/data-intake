"""Quality checks. Each takes a TableContext and returns client-readable findings."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from data_intake.kinds import ColumnAnalysis, analyse_column
from data_intake.models import RawTable

MAX_EXAMPLES = 5


@dataclass
class TableContext:
    """A table with each column analysed once, shared by every check."""

    table: RawTable
    columns: dict[str, ColumnAnalysis]
    as_of: date

    @classmethod
    def build(cls, table: RawTable, as_of: date) -> "TableContext":
        analyses = {
            name: analyse_column(name, table.column_values(index))
            for index, name in enumerate(table.columns)
        }
        return cls(table, analyses, as_of)

    def values(self, column: str) -> list[str | None]:
        return self.table.column_values(self.table.columns.index(column))


def examples(values: Iterable[object], limit: int = MAX_EXAMPLES) -> list[str]:
    """First few distinct values as display strings, each cut to 40 characters."""
    seen: list[str] = []
    for value in values:
        text = repr(value) if isinstance(value, str) and value != value.strip() else str(value)
        text = text if len(text) <= 40 else text[:37] + "..."
        if text not in seen:
            seen.append(text)
        if len(seen) == limit:
            break
    return seen


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "0%"
