"""Values that are possible but suspicious: extreme numbers, negatives, odd dates."""

import re
import statistics
from datetime import date

from data_intake.checks import TableContext, examples
from data_intake.kinds import parse_date, parse_number
from data_intake.models import Finding, Severity

AMOUNT_NAME = re.compile(r"(amount|price|total|revenue|cost|fee|hours|qty|quantity)", re.I)
IQR_FENCE = 3.0
EARLIEST_PLAUSIBLE = date(1990, 1, 1)
MIN_VALUES_FOR_OUTLIERS = 20


def check(ctx: TableContext) -> list[Finding]:
    findings: list[Finding] = []
    for name, column in ctx.columns.items():
        if column.kind in {"integer", "decimal", "currency"}:
            numbers = [n for v in ctx.values(name) if (n := parse_number(v)) is not None]
            findings += _extremes(ctx, name, numbers)
            findings += _negatives(ctx, name, numbers)
        elif column.kind == "date":
            dates = [d for v in ctx.values(name) if (d := parse_date(v)) is not None]
            findings += _odd_dates(ctx, name, dates)
    return findings


def _extremes(ctx: TableContext, name: str, numbers: list[float]) -> list[Finding]:
    if len(numbers) < MIN_VALUES_FOR_OUTLIERS:
        return []
    q1, _, q3 = statistics.quantiles(numbers, n=4)
    spread = q3 - q1
    if spread == 0:
        return []
    low, high = q1 - IQR_FENCE * spread, q3 + IQR_FENCE * spread
    outliers = sorted((n for n in numbers if n < low or n > high), key=abs, reverse=True)
    if not outliers:
        return []
    return [
        Finding(
            code="outliers",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Unusually large or small values",
            detail=f"{len(outliers)} values sit far outside the typical range "
            f"({_fmt(q1)} to {_fmt(q3)} for the middle half).",
            impact="Could be real (a big order) or an entry error (an extra zero). Averages "
            "will be pulled toward them either way; worth confirming.",
            examples=examples(_fmt(n) for n in outliers),
            affected_rows=len(outliers),
        )
    ]


def _negatives(ctx: TableContext, name: str, numbers: list[float]) -> list[Finding]:
    negatives = [n for n in numbers if n < 0]
    if not negatives or not AMOUNT_NAME.search(name):
        return []
    return [
        Finding(
            code="negative_amounts",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Negative values where amounts are expected",
            detail=f"{len(negatives)} values are below zero.",
            impact="Often refunds or corrections. Totals are right only if that is intended; "
            "averages and counts of sales are not.",
            examples=examples(_fmt(n) for n in negatives),
            affected_rows=len(negatives),
        )
    ]


def _odd_dates(ctx: TableContext, name: str, dates: list[date]) -> list[Finding]:
    findings: list[Finding] = []
    future = sorted(d for d in dates if d > ctx.as_of)
    if future:
        findings.append(
            Finding(
                code="future_dates",
                severity=Severity.WARNING,
                table=ctx.table.name,
                column=name,
                title="Dates after the export date",
                detail=f"{len(future)} dates are later than {ctx.as_of.isoformat()}.",
                impact="Usually typos in the year or scheduled items mixed in with actuals; "
                "they land in the wrong period in any time series.",
                examples=examples(d.isoformat() for d in future),
                affected_rows=len(future),
            )
        )
    ancient = sorted(d for d in dates if d < EARLIEST_PLAUSIBLE)
    if ancient:
        findings.append(
            Finding(
                code="implausible_dates",
                severity=Severity.WARNING,
                table=ctx.table.name,
                column=name,
                title="Dates too old to be real",
                detail=f"{len(ancient)} dates are before {EARLIEST_PLAUSIBLE.year}.",
                impact="Often a default like 1900-01-01 standing in for 'unknown'.",
                examples=examples(d.isoformat() for d in ancient),
                affected_rows=len(ancient),
            )
        )
    return findings


def _fmt(number: float) -> str:
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"
