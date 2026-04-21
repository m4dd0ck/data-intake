from datetime import date
from pathlib import Path

from data_intake.audit import run_audit


def test_audit_profiles_tables_and_orders_findings(tmp_path: Path) -> None:
    (tmp_path / "orders.csv").write_text(
        "order_id,order_date,customer_id,amount\n"
        "1,2024-01-02,C1,$10.00\n2,2024-01-03,C2,12.00\n2,2024-01-03,C2,12.00\n"
        "3,1/4/2024,C9,8.00\n"
    )
    (tmp_path / "customers.csv").write_text("customer_id,name\nC1,Ana\nC2,Bo\n")
    audit = run_audit(tmp_path, "Test Co", as_of=date(2024, 6, 30))

    assert [t.name for t in audit.tables] == ["customers", "orders"]
    orders = next(t for t in audit.tables if t.name == "orders")
    assert {c.name: c.kind for c in orders.columns}["order_date"] == "date"
    assert audit.findings[0].severity == "critical"  # sorted most severe first
    codes = {f.code for f in audit.findings}
    assert {"duplicate_rows", "mixed_date_formats", "numbers_as_text", "orphan_keys"} <= codes
    assert any(k.name.startswith("Revenue") for k in audit.kpis)
