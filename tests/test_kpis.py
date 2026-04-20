from conftest import context

from data_intake.kpis import suggest


def test_orders_shape_suggests_revenue_aov_and_cohorts() -> None:
    orders = context(
        ["order_id", "order_date", "customer_id", "amount"],
        [[str(i), "2024-01-0" + str(1 + i % 9), f"C{i % 4}", "10.50"] for i in range(30)],
        "orders",
    )
    names = [s.name for s in suggest([orders])]
    assert names == [
        "Revenue and orders by month",
        "Average order value and repeat purchase rate",
        "Customer cohort retention",
    ]


def test_invoices_and_timesheets() -> None:
    invoices = context(
        ["invoice_id", "issued", "amount", "paid_on"],
        [[f"I{i}", "2024-02-01", "100", "2024-02-10"] for i in range(5)],
        "invoices",
    )
    timesheets = context(
        ["date", "client_id", "hours"], [["2024-02-01", "C1", "3.5"]] * 5, "timesheets"
    )
    names = {s.name for s in suggest([invoices, timesheets])}
    assert names == {"Billed vs collected, and days to pay", "Billable hours and utilisation"}
