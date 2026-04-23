"""Run every check over a folder of exports and collect the results into one Audit."""

from datetime import date
from pathlib import Path

from data_intake.checks import (
    TableContext,
    duplicates,
    examples,
    formats,
    missing,
    outliers,
    structure,
)
from data_intake.kinds import is_blank, parse_date, parse_number
from data_intake.kpis import suggest
from data_intake.loaders import load_folder
from data_intake.models import SEVERITY_ORDER, Audit, ColumnProfile, Finding, TableProfile
from data_intake.relations import find_joins

CHECKS = (structure.check, missing.check, formats.check, duplicates.check, outliers.check)


def run_audit(folder: Path, client: str, as_of: date | None = None) -> Audit:
    """Audit every CSV and Excel file in ``folder``.

    Args:
        folder: Directory of client exports.
        client: Name shown on the report.
        as_of: Date the data was exported; dates after it are flagged. Defaults to today.
    """
    as_of = as_of or date.today()
    contexts = [TableContext.build(t, as_of) for t in load_folder(folder)]
    findings: list[Finding] = [
        finding for ctx in contexts for check in CHECKS for finding in check(ctx)
    ]
    joins, join_findings = find_joins(contexts)
    findings += join_findings
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.table, f.column or "", f.code))
    return Audit(
        client=client,
        as_of=as_of,
        tables=[profile_table(ctx) for ctx in contexts],
        findings=findings,
        joins=joins,
        kpis=suggest(contexts),
    )


def profile_table(ctx: TableContext) -> TableProfile:
    columns = []
    for name, column in ctx.columns.items():
        present = [v.strip() for v in ctx.values(name) if not is_blank(v) and v]
        low, high = _range(column.kind, present)
        columns.append(
            ColumnProfile(
                name=name,
                kind=column.kind,
                non_empty=column.non_blank,
                distinct=column.distinct,
                examples=examples(present, limit=3),
                minimum=low,
                maximum=high,
            )
        )
    return TableProfile(
        name=ctx.table.name,
        source=ctx.table.source.name,
        rows=len(ctx.table.rows),
        columns=columns,
        header_row=ctx.table.header_row,
    )


def _range(kind: str, values: list[str]) -> tuple[str | None, str | None]:
    if kind == "date":
        dates = sorted(d for v in values if (d := parse_date(v)))
        return (dates[0].isoformat(), dates[-1].isoformat()) if dates else (None, None)
    if kind in {"integer", "decimal", "currency", "percent"}:
        numbers = sorted(n for v in values if (n := parse_number(v)) is not None)
        return (f"{numbers[0]:,.2f}", f"{numbers[-1]:,.2f}") if numbers else (None, None)
    return None, None
