from datetime import date
from pathlib import Path

from data_intake.audit import run_audit
from data_intake.report import render_html, write_reports


def test_report_escapes_client_data_and_is_self_contained(tmp_path: Path) -> None:
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "notes.csv").write_text('id,note\n1,"<script>alert(1)</script>"\n1,x\n')
    audit = run_audit(exports, "Acme <Ltd>", as_of=date(2024, 6, 30))
    html = render_html(audit)
    assert "<script>alert(1)" not in html
    assert "Acme &lt;Ltd&gt;" in html
    assert "<link" not in html and "src=" not in html  # no external assets

    write_reports(audit, tmp_path / "out/report.html", tmp_path / "out/findings.json")
    assert (tmp_path / "out/findings.json").read_text().startswith("{")
