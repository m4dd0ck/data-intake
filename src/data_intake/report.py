"""Write an audit as a self-contained HTML page and as JSON."""

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from data_intake.models import Audit

_env = Environment(
    loader=PackageLoader("data_intake", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_html(audit: Audit) -> str:
    """One HTML file with inline styles, readable offline and safe to email."""
    template = _env.get_template("report.html.j2")
    return template.render(
        audit=audit,
        files=sorted({table.source for table in audit.tables}),
        total_rows=sum(table.rows for table in audit.tables),
    )


def write_reports(audit: Audit, html_path: Path | None, json_path: Path | None) -> None:
    if html_path:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_html(audit), encoding="utf-8")
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(audit.model_dump_json(indent=2) + "\n", encoding="utf-8")


def without_examples(audit: Audit) -> Audit:
    """Copy of the audit with every example value removed, for reports that leave the client."""
    return audit.model_copy(
        update={
            "findings": [f.model_copy(update={"examples": []}) for f in audit.findings],
            "tables": [
                t.model_copy(
                    update={
                        "columns": [
                            c.model_copy(update={"examples": [], "minimum": None, "maximum": None})
                            for c in t.columns
                        ]
                    }
                )
                for t in audit.tables
            ],
        }
    )
