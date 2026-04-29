"""Missing data: empty cells and the placeholders people type instead."""

from data_intake.checks import TableContext, counted, examples, percent
from data_intake.models import Finding, Severity

HIGH_MISSING = 0.2


def check(ctx: TableContext) -> list[Finding]:
    findings: list[Finding] = []
    total = len(ctx.table.rows)
    for name, column in ctx.columns.items():
        if column.kind == "empty" or not total:
            continue  # structure check reports empty columns
        placeholders = sum(column.blank_tokens.values())
        if placeholders:
            findings.append(
                Finding(
                    code="blank_placeholders",
                    severity=Severity.WARNING,
                    table=ctx.table.name,
                    column=name,
                    title="Missing values written as text",
                    detail=counted(
                        placeholders, "cell holds a placeholder", "cells hold placeholders"
                    )
                    + " instead of being empty.",
                    impact="Tools will treat these as real values: counts of distinct values "
                    "and joins on this column will be wrong until they are blanked.",
                    examples=examples(column.blank_tokens),
                    affected_rows=placeholders,
                )
            )
        missing = total - column.non_blank
        if missing / total >= HIGH_MISSING:
            findings.append(
                Finding(
                    code="high_missing",
                    severity=Severity.WARNING if missing / total < 0.6 else Severity.INFO,
                    table=ctx.table.name,
                    column=name,
                    title=f"{percent(missing, total)} of values are missing",
                    detail=f"{missing} of {total} "
                    + ("row has" if total == 1 else "rows have")
                    + f" no {name}.",
                    impact="Any breakdown by this column will leave these rows out or lump "
                    "them into an unknown bucket.",
                    affected_rows=missing,
                )
            )
    return findings
