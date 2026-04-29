"""Duplicates: repeated rows, keys that should be unique, and near-duplicate records."""

import re
from collections import defaultdict

from rapidfuzz import fuzz

from data_intake.checks import TableContext, counted, examples
from data_intake.kinds import ID_NAME, is_blank
from data_intake.models import Finding, Severity

NAME_LIKE = re.compile(r"(name|customer|client|company|contact)", re.IGNORECASE)
SIMILARITY = 92
DIGITS = re.compile(r"\d+")
MAX_FUZZY_VALUES = 3000


def check(ctx: TableContext) -> list[Finding]:
    return [*_duplicate_rows(ctx), *_duplicate_keys(ctx), *_near_duplicates(ctx)]


def _normalised_rows(ctx: TableContext) -> list[tuple[str, ...]]:
    return [tuple("" if c is None else c.strip() for c in row) for row in ctx.table.rows]


def _duplicate_rows(ctx: TableContext) -> list[Finding]:
    rows = _normalised_rows(ctx)
    extra = len(rows) - len(set(rows))
    if not extra:
        return []
    return [
        Finding(
            code="duplicate_rows",
            severity=Severity.CRITICAL,
            table=ctx.table.name,
            title="Rows repeated exactly",
            detail=counted(extra, "row is an exact copy", "rows are exact copies")
            + " of another row.",
            impact="Every count and total from this file is overstated until copies are removed.",
            affected_rows=extra,
        )
    ]


def _duplicate_keys(ctx: TableContext) -> list[Finding]:
    """Key-like columns that are nearly unique but repeat on rows that disagree."""
    findings: list[Finding] = []
    unique_rows = set(_normalised_rows(ctx))
    for position, (name, column) in enumerate(ctx.columns.items()):
        looks_like_key = column.kind == "id" or (position == 0 and ID_NAME.search(name))
        if not looks_like_key or column.non_blank == 0:
            continue
        if column.distinct < 0.9 * column.non_blank:
            continue  # repeats by design (e.g. customer_id on orders)
        rows_by_key: dict[str, set[tuple[str, ...]]] = defaultdict(set)
        index = ctx.table.columns.index(name)
        for row in unique_rows:
            if not is_blank(row[index]):
                rows_by_key[row[index]].add(row)
        conflicting = sorted(key for key, rows in rows_by_key.items() if len(rows) > 1)
        if conflicting:
            findings.append(
                Finding(
                    code="duplicate_keys",
                    severity=Severity.CRITICAL,
                    table=ctx.table.name,
                    column=name,
                    title="The same ID appears on different rows",
                    detail=counted(
                        len(conflicting), f"{name} value appears", f"{name} values appear"
                    )
                    + " on rows with different contents.",
                    impact="These are not simple copies: one of each pair is probably an edit "
                    "or a mistake, and someone has to decide which row is right.",
                    examples=examples(conflicting),
                    affected_rows=sum(len(rows_by_key[key]) for key in conflicting),
                )
            )
    return findings


def _near_duplicates(ctx: TableContext) -> list[Finding]:
    findings: list[Finding] = []
    for name, column in ctx.columns.items():
        if column.kind == "email":
            findings += _email_case_variants(ctx, name)
        elif NAME_LIKE.search(name) and column.kind in {"text", "category"}:
            findings += _similar_names(ctx, name)
    return findings


def _email_case_variants(ctx: TableContext, name: str) -> list[Finding]:
    forms: dict[str, set[str]] = defaultdict(set)
    for value in ctx.values(name):
        if not is_blank(value):
            assert value is not None
            forms[value.strip().lower()].add(value.strip())
    variants = [" / ".join(sorted(f)) for f in forms.values() if len(f) > 1]
    if not variants:
        return []
    return [
        Finding(
            code="near_duplicate_records",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="The same email address in different capitalisation",
            detail=counted(len(variants), "address appears", "addresses appear")
            + " in different letter case.",
            impact="These are almost certainly the same person counted as separate customers.",
            examples=variants[:5],
            affected_rows=len(variants),
        )
    ]


def _likely_same(left: str, right: str) -> bool:
    """Nearly identical text that is not simply a different number ("Item 1" vs "Item 11")."""
    if left.lower() == right.lower() or DIGITS.findall(left) != DIGITS.findall(right):
        return False
    return fuzz.token_sort_ratio(left, right) >= SIMILARITY


def _similar_names(ctx: TableContext, name: str) -> list[Finding]:
    distinct = sorted({" ".join(v.split()) for v in ctx.values(name) if not is_blank(v) and v})
    if len(distinct) > MAX_FUZZY_VALUES:
        return []
    # Reason: compare within first-letter blocks; near-duplicates rarely differ there, and it
    # keeps the pairwise comparison small.
    blocks: dict[str, list[str]] = defaultdict(list)
    for value in distinct:
        blocks[value[:1].lower()].append(value)
    pairs = []
    for block in blocks.values():
        for i, left in enumerate(block):
            for right in block[i + 1 :]:
                if _likely_same(left, right):
                    pairs.append(f"{left} / {right}")
    if not pairs:
        return []
    return [
        Finding(
            code="near_duplicate_records",
            severity=Severity.WARNING,
            table=ctx.table.name,
            column=name,
            title="Names that look like the same record",
            detail=counted(len(pairs), "pair", "pairs")
            + f" of {name} values "
            + ("is" if len(pairs) == 1 else "are")
            + " nearly identical.",
            impact="Likely typos or re-entered records; counts of unique customers or clients "
            "will be too high until they are merged.",
            examples=pairs[:5],
            affected_rows=len(pairs),
        )
    ]
