import re
from pathlib import Path

from typer.testing import CliRunner

from data_intake.cli import app


def test_summary_line_uses_the_singular_for_one(tmp_path: Path) -> None:
    (tmp_path / "orders.csv").write_text("order_id,amount\n1,10\n2,20\n")
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--client", "Acme", "--out", str(tmp_path / "a.html")]
    )
    assert result.exit_code == 0, result.output
    assert "1 table," in result.output
    assert not re.search(r"\b1 (tables|warnings|notes)\b", result.output)
