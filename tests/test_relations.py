from conftest import context

from data_intake.relations import find_joins


def test_foreign_key_join_with_orphans() -> None:
    clients = context(
        ["client_id", "name"], [[f"C{i}", f"Client {i}"] for i in range(10)], "clients"
    )
    timesheets = context(
        ["Client ID", "hours"], [["C1", "2"], ["C2", "3"], ["C99", "1"], ["C1", "4"]], "timesheets"
    )
    joins, findings = find_joins([clients, timesheets])
    join = next(j for j in joins if j.left_table == "timesheets")
    assert (join.left_column, join.right_table, join.right_column) == (
        "Client ID",
        "clients",
        "client_id",
    )
    assert join.orphan_values == 1
    assert findings[0].code == "orphan_keys"
    assert findings[0].examples == ["c99"]


def test_unrelated_columns_do_not_join() -> None:
    orders = context(["order_id", "country"], [[str(i), "US"] for i in range(10)], "orders")
    products = context(["sku", "price"], [[f"S{i}", "9"] for i in range(10)], "products")
    assert find_joins([orders, products]) == ([], [])
