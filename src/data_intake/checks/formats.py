"""Format problems: mixed date styles, numbers stored as text, currencies, labels, whitespace."""

import re
from collections import defaultdict

from data_intake.checks import TableContext, examples
from data_intake.kinds import DATE_KINDS, NUMBER_KINDS, is_blank, value_kind
from data_intake.models import Finding, Severity

CURRENCY_MARK = re.compile(r"[$€£¥]|\b(USD|EUR|GBP|CAD|AUD)\b", re.IGNORECASE)
SYMBOL_CODES = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
DATE_NAME = re.compile(r"(date|_at$|_on$|issued|created|updated|day)", re.IGNORECASE)
DATE_KIND_LABELS = {
    "date_iso": "2024-03-04",
    "datetime": "2024-03-04 10:15",
    "date_slash": "03/04/2024",
    "date_dot": "04.03.2024",
    "date_text": "Mar 4, 2024",
}


def check(ctx: TableContext) -> list[Finding]:
    findings: list[Finding] = []
    for name, column in ctx.columns.items():
        values = [v for v in ctx.values(name) if not is_blank(v)]
        present = [v for v in values if v is not None]
        if not present:
            continue
        if column.kind == "date":
            findings += _mixed_dates(ctx, name, present)
        if column.kind in {"currency", "decimal", "integer"}:
            findings += _numbers_as_text(ctx, name, present)
            findings += _non_numbers(ctx, name, present)
        if column.kind in {"integer", "id"} and DATE_NAME.search(name):
            findings += _excel_serials(ctx, name, present)
        if column.kind == "category":
            findings += _inconsistent_labels(ctx, name, present)
        findings += _whitespace(ctx, name, present)
    return findings


def _mixed_dates(ctx: TableContext, name: str, values: list[str]) -> list[Finding]:
    styles: dict[str, list[str]] = defaultdict(list)
    for value in values:
        kind = value_kind(value)
        if kind in DATE_KINDS:
            styles["date_iso" if kind == "datetime" else kind].append(value)
    if len(styles) < 2:
        return []
    breakdown = ", ".join(
        f"{len(found)} like {DATE_KIND_LABELS[kind]}" for kind, found in styles.items()
    )
    return [
        Finding(
            code="mixed_date_formats",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Dates are written in more than one format",
            detail=f"{breakdown}.",
            impact="Dates like 03/04/2024 are ambiguous (March 4 or April 3), and sorting or "
            "monthly totals will be wrong until one format is used.",
            examples=[found[0] for found in styles.values()],
            affected_rows=sum(len(found) for found in styles.values())
            - max(map(len, styles.values())),
        )
    ]


def _numbers_as_text(ctx: TableContext, name: str, values: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    formatted = [v for v in values if CURRENCY_MARK.search(v) or "," in v]
    if formatted:
        findings.append(
            Finding(
                code="numbers_as_text",
                severity=Severity.WARNING,
                table=ctx.table.name,
                column=name,
                title="Numbers stored with currency symbols or separators",
                detail=f"{len(formatted)} values include symbols or thousands separators.",
                impact="Spreadsheets and databases read these as text, so they drop out of sums "
                "and averages unless they are cleaned first.",
                examples=examples(formatted),
                affected_rows=len(formatted),
            )
        )
    currencies = {_currency_of(v) for v in values} - {None}
    if len(currencies) > 1:
        findings.append(
            Finding(
                code="mixed_currencies",
                severity=Severity.CRITICAL,
                table=ctx.table.name,
                column=name,
                title="More than one currency in the same column",
                detail=f"Found {', '.join(sorted(c for c in currencies if c))}.",
                impact="Totals would add different currencies together. Each value needs "
                "converting to one currency (with the rate and date used) before any sum.",
                examples=examples(v for v in values if _currency_of(v)),
            )
        )
    return findings


def _currency_of(value: str) -> str | None:
    match = CURRENCY_MARK.search(value)
    if not match:
        return None
    token = match.group(0)
    return SYMBOL_CODES.get(token, token.upper())


def _non_numbers(ctx: TableContext, name: str, values: list[str]) -> list[Finding]:
    stray = [v for v in values if value_kind(v) not in NUMBER_KINDS]
    if not stray:
        return []
    return [
        Finding(
            code="non_numeric_values",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Text mixed into a number column",
            detail=f"{len(stray)} values are not numbers.",
            impact="These rows will fail or be skipped in any calculation on this column.",
            examples=examples(stray),
            affected_rows=len(stray),
        )
    ]


def _excel_serials(ctx: TableContext, name: str, values: list[str]) -> list[Finding]:
    serials = [v for v in values if v.isdigit() and 20000 <= int(v) <= 80000]
    if len(serials) < 0.5 * len(values):
        return []
    return [
        Finding(
            code="excel_serial_dates",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Dates saved as Excel serial numbers",
            detail=f"{len(serials)} values look like Excel day counts (e.g. 45412 = 2024-04-30).",
            impact="They sort correctly but read as numbers; they need converting before any "
            "date grouping or display.",
            examples=examples(serials),
            affected_rows=len(serials),
        )
    ]


def _inconsistent_labels(ctx: TableContext, name: str, values: list[str]) -> list[Finding]:
    variants: dict[str, set[str]] = defaultdict(set)
    for value in values:
        variants[" ".join(value.split()).lower()].add(value)
    clashing = {key: forms for key, forms in variants.items() if len(forms) > 1}
    if not clashing:
        return []
    shown = [" / ".join(sorted(repr(f) for f in forms)) for forms in clashing.values()]
    return [
        Finding(
            code="inconsistent_labels",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="The same label is spelled several ways",
            detail=f"{len(clashing)} labels differ only by case or spacing.",
            impact="Breakdowns will split one group into several (e.g. 'US' and 'us ' "
            "counted separately).",
            examples=shown[:5],
            affected_rows=sum(1 for v in values if " ".join(v.split()).lower() in clashing),
        )
    ]


def _whitespace(ctx: TableContext, name: str, raw: list[str]) -> list[Finding]:
    padded = [v for v in raw if v != v.strip()]
    if not padded:
        return []
    return [
        Finding(
            code="stray_whitespace",
            severity=Severity.INFO,
            table=ctx.table.name,
            column=name,
            title="Values with leading or trailing spaces",
            detail=f"{len(padded)} values have extra spaces.",
            impact="Invisible, but 'Leeds' and 'Leeds ' will not match in lookups or joins.",
            examples=examples(padded),
            affected_rows=len(padded),
        )
    ]
