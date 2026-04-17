"""How files relate: likely join keys, and keys that point at nothing."""

from itertools import permutations

from rapidfuzz import fuzz

from data_intake.checks import TableContext, examples
from data_intake.kinds import ColumnAnalysis, is_blank
from data_intake.models import Finding, JoinCandidate, Severity

MIN_CONTAINMENT = 0.5
NAME_SIMILARITY = 85
TEXTUAL_KINDS = {"id", "integer", "text", "category", "email"}


def _key_name(column: str) -> str:
    """``client_id`` and ``Client ID`` both become ``client``."""
    name = column.lower().replace(" ", "_")
    for suffix in ("_id", "id", "_code", "_no"):
        name = name.removesuffix(suffix)
    return name.strip("_")


def _values(ctx: TableContext, column: str) -> set[str]:
    return {v.strip().lower() for v in ctx.values(column) if not is_blank(v) and v}


def _is_key(column: ColumnAnalysis) -> bool:
    """Nearly unique values, like a primary key another file could refer to."""
    return column.kind in TEXTUAL_KINDS and column.distinct >= 0.9 * column.non_blank > 0


def find_joins(contexts: list[TableContext]) -> tuple[list[JoinCandidate], list[Finding]]:
    """Column pairs where one side looks like a key the other side refers to."""
    joins: list[JoinCandidate] = []
    findings: list[Finding] = []
    for left, right in permutations(contexts, 2):
        for right_name, right_col in right.columns.items():
            if not _is_key(right_col):
                continue
            right_values = _values(right, right_name)
            for left_name, left_col in left.columns.items():
                similar = fuzz.ratio(_key_name(left_name), _key_name(right_name))
                if left_col.kind not in TEXTUAL_KINDS or similar < NAME_SIMILARITY:
                    continue
                left_values = _values(left, left_name)
                if not left_values:
                    continue
                containment = len(left_values & right_values) / len(left_values)
                if containment < MIN_CONTAINMENT:
                    continue
                orphans = sorted(left_values - right_values)
                joins.append(
                    JoinCandidate(
                        left_table=left.table.name,
                        left_column=left_name,
                        right_table=right.table.name,
                        right_column=right_name,
                        containment=round(containment, 3),
                        orphan_values=len(orphans),
                    )
                )
                if orphans:
                    findings.append(_orphans(left, left_name, right, right_name, orphans))
    return joins, findings


def _orphans(
    left: TableContext, column: str, right: TableContext, right_column: str, orphans: list[str]
) -> Finding:
    return Finding(
        code="orphan_keys",
        severity=Severity.WARNING,
        table=left.table.name,
        column=column,
        title=f"Values with no match in {right.table.name}",
        detail=f"{len(orphans)} {column} values do not exist in {right.table.name}.{right_column}.",
        impact="Rows with these values drop out of any report that joins the two files, "
        "usually because the reference list is out of date.",
        examples=examples(orphans),
        affected_rows=len(orphans),
    )
