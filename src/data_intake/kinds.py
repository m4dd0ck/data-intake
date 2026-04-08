"""Work out what a text column really holds, and parse its values.

Every value is classified on its own (``value_kind``), then a column's kind is the kind most of
its non-blank values share. The per-value counts are kept, because a column that is 80% ISO
dates and 20% US dates is exactly what the format checks need to report.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

BLANK_TOKENS = {"", "n/a", "na", "-", "--", "null", "none", "?", "nan", "#n/a", "missing"}

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("integer", re.compile(r"^[+-]?\d+$")),
    ("decimal", re.compile(r"^[+-]?(\d{1,3}(,\d{3})+(\.\d+)?|\d+\.\d+|\.\d+)$")),
    ("currency", re.compile(r"^[+-]?\s*[$€£¥]\s*[\d,]*\.?\d+$|^[+-]?[\d,]*\.?\d+\s*[$€£¥]$")),
    ("currency", re.compile(r"^(USD|EUR|GBP|CAD|AUD)\s*[+-]?[\d,]*\.?\d+$", re.IGNORECASE)),
    ("percent", re.compile(r"^[+-]?\d+(\.\d+)?\s*%$")),
    ("date_iso", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("datetime", re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?")),
    ("date_slash", re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")),
    ("date_dot", re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")),
    ("date_text", re.compile(r"^[A-Za-z]{3,9}\.? \d{1,2},? \d{4}$")),
    ("boolean", re.compile(r"^(true|false|yes|no|y|n)$", re.IGNORECASE)),
    ("email", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
]
DATE_KINDS = {"date_iso", "datetime", "date_slash", "date_dot", "date_text"}
NUMBER_KINDS = {"integer", "decimal", "currency", "percent"}
ID_NAME = re.compile(r"(^id$|_id$|id$|_code$|_number$|_no$|^sku$)", re.IGNORECASE)
MAJORITY = 0.9


def is_blank(value: str | None) -> bool:
    """True for empty cells and the placeholders people type for "no value"."""
    return value is None or value.strip().lower() in BLANK_TOKENS


def value_kind(value: str) -> str:
    """Kind of one non-blank value; ``text`` when nothing more specific fits."""
    stripped = value.strip()
    for kind, pattern in _PATTERNS:
        if pattern.match(stripped):
            return kind
    return "text"


@dataclass
class ColumnAnalysis:
    """What a column holds: overall kind plus the evidence behind it."""

    kind: str
    non_blank: int
    distinct: int
    value_kinds: Counter[str] = field(default_factory=Counter)
    blank_tokens: Counter[str] = field(default_factory=Counter)


def analyse_column(name: str, values: list[str | None]) -> ColumnAnalysis:
    """Classify a column from its name and values."""
    blank_tokens: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    present: list[str] = []
    for value in values:
        if is_blank(value):
            if value is not None:
                blank_tokens[value] += 1
            continue
        assert value is not None
        present.append(value.strip())
        kinds[value_kind(value)] += 1

    distinct = len(set(present))
    analysis = ColumnAnalysis("empty", len(present), distinct, kinds, blank_tokens)
    if not present:
        return analysis
    analysis.kind = _overall_kind(name, kinds, len(present), distinct)
    return analysis


def _overall_kind(name: str, kinds: Counter[str], total: int, distinct: int) -> str:
    def share(group: set[str]) -> float:
        return sum(kinds[k] for k in group) / total

    if share(DATE_KINDS) >= MAJORITY:
        return "date"
    if share(NUMBER_KINDS) >= MAJORITY:
        if kinds["currency"]:
            return "currency"
        if kinds["percent"] / total >= MAJORITY:
            return "percent"
        is_whole = kinds["integer"] / total >= MAJORITY
        if is_whole and ID_NAME.search(name) and distinct >= 0.9 * total:
            return "id"
        return "integer" if is_whole else "decimal"
    top_kind, top_count = kinds.most_common(1)[0]
    if top_count / total >= MAJORITY and top_kind in {"boolean", "email"}:
        return top_kind
    if ID_NAME.search(name) and distinct >= 0.5 * total:
        return "id"
    if distinct <= max(20, total // 20):
        return "category"
    return "text"


def parse_number(value: str | None) -> float | None:
    """Number from plain, thousands-separated, currency or percent text; None if not numeric."""
    if is_blank(value):
        return None
    assert value is not None
    kind = value_kind(value)
    if kind not in NUMBER_KINDS:
        return None
    cleaned = re.sub(r"(?i)usd|eur|gbp|cad|aud|[$€£¥,%\s]", "", value)
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number / 100 if kind == "percent" else number


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
)}  # fmt: skip


def parse_date(value: str | None) -> date | None:
    """Date from ISO, slash (US unless the first part exceeds 12), dotted or "Mar 4, 2024"."""
    if is_blank(value):
        return None
    assert value is not None
    text = value.strip()
    kind = value_kind(text)
    try:
        if kind in {"date_iso", "datetime"}:
            return date.fromisoformat(text[:10])
        if kind == "date_slash":
            first, second, year = (int(p) for p in text.split("/"))
            month, day = (second, first) if first > 12 else (first, second)
            return date(year, month, day)
        if kind == "date_dot":
            day, month, year = (int(p) for p in text.split("."))
            return date(year, month, day)
        if kind == "date_text":
            month_name, day_text, year_text = text.replace(",", "").replace(".", "").split()
            return date(int(year_text), _MONTHS[month_name[:3].lower()], int(day_text))
    except (ValueError, KeyError):
        return None
    return None
