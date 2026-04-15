"""Problems with the shape of a file: title rows, headers, empty columns."""

from data_intake.checks import TableContext
from data_intake.models import Finding, Severity


def check(ctx: TableContext) -> list[Finding]:
    table = ctx.table
    findings: list[Finding] = []
    if table.header_row > 0:
        findings.append(
            Finding(
                code="title_rows",
                severity=Severity.INFO,
                table=table.name,
                title="Title rows above the header",
                detail=f"The header is on row {table.header_row + 1}; the rows above it were "
                "skipped.",
                impact="Fine for this audit, but anything that assumes row 1 is the header "
                "will read the title as column names.",
            )
        )
    if table.renamed_columns:
        shown = [
            f"{new} (was {old!r})" if old else f"{new} (was blank)"
            for new, old in table.renamed_columns.items()
        ]
        findings.append(
            Finding(
                code="bad_headers",
                severity=Severity.WARNING,
                table=table.name,
                title="Blank, padded or repeated column names",
                detail=f"{len(shown)} headers were renamed to make them usable.",
                impact="Repeated names usually mean two different fields share a label; "
                "someone who knows the export should say which is which.",
                examples=shown[:5],
            )
        )
    empty = [name for name, column in ctx.columns.items() if column.kind == "empty"]
    if empty and table.rows:
        findings.append(
            Finding(
                code="empty_columns",
                severity=Severity.INFO,
                table=table.name,
                title="Columns with no data",
                detail=f"{len(empty)} columns are completely empty.",
                impact="Safe to drop, unless the field was expected to be filled.",
                examples=empty[:5],
            )
        )
    return findings
