"""Which standard metrics the data can support, based on the shape of each table.

Rule-based on purpose: a client should be able to read the "why" and see which columns make a
metric possible.
"""

import re

from data_intake.checks import TableContext
from data_intake.models import KpiSuggestion

CUSTOMER = re.compile(r"(customer|client|account|buyer)", re.I)
AMOUNT = re.compile(r"(amount|total|price|revenue|value|subtotal)", re.I)
HOURS = re.compile(r"(hours|duration|time_spent)", re.I)
PAID = re.compile(r"(paid|payment|settled)", re.I)
DUE = re.compile(r"(due)", re.I)
LOCATION = re.compile(r"(country|city|region|state|postcode|zip)", re.I)
PRODUCT = re.compile(r"(product|sku|item)", re.I)
COST = re.compile(r"(cost|cogs)", re.I)


def _find(ctx: TableContext, pattern: re.Pattern[str], kinds: set[str] | None = None) -> str | None:
    for name, column in ctx.columns.items():
        if pattern.search(name) and (kinds is None or column.kind in kinds):
            return name
    return None


def _date_column(ctx: TableContext) -> str | None:
    return next((n for n, c in ctx.columns.items() if c.kind == "date"), None)


MONEY = {"currency", "decimal", "integer"}


def suggest(contexts: list[TableContext]) -> list[KpiSuggestion]:
    suggestions: list[KpiSuggestion] = []
    for ctx in contexts:
        name = ctx.table.name
        when = _date_column(ctx)
        amount = _find(ctx, AMOUNT, MONEY)
        customer = _find(ctx, CUSTOMER)
        if "invoice" in name.lower() and when and amount:
            suggestions.append(KpiSuggestion(
                name="Billed vs collected, and days to pay",
                tables=[name],
                why=f"{when} and {amount} give billing by month"
                + (f"; {_find(ctx, PAID)} shows what was collected" if _find(ctx, PAID) else "")
                + (f"; {_find(ctx, DUE)} allows overdue ageing" if _find(ctx, DUE) else "")
                + ".",
            ))  # fmt: skip
        elif when and amount and customer:
            suggestions += [
                KpiSuggestion(
                    name="Revenue and orders by month",
                    tables=[name],
                    why=f"{when} and {amount} are enough for monthly revenue and order counts.",
                ),
                KpiSuggestion(
                    name="Average order value and repeat purchase rate",
                    tables=[name],
                    why=f"{customer} links orders to buyers, so repeat buying is measurable.",
                ),
                KpiSuggestion(
                    name="Customer cohort retention",
                    tables=[name],
                    why=f"First order month per {customer} defines cohorts; later months show "
                    "who comes back.",
                ),
            ]
        hours = _find(ctx, HOURS, MONEY)
        if hours and when:
            suggestions.append(
                KpiSuggestion(
                    name="Billable hours and utilisation",
                    tables=[name],
                    why=f"{hours} per {when}"
                    + (f" per {customer}" if customer else "")
                    + " gives hours by week and client; with invoices, an effective hourly rate.",
                )
            )
        if customer and _find(ctx, LOCATION) and not amount:
            suggestions.append(
                KpiSuggestion(
                    name="Customer base by location" + (" and signup month" if when else ""),
                    tables=[name],
                    why=f"{_find(ctx, LOCATION)} gives geography"
                    + (f" and {when} gives growth over time." if when else "."),
                )
            )
        if _find(ctx, PRODUCT) and amount and not customer:
            has_cost = _find(ctx, COST, MONEY)
            suggestions.append(
                KpiSuggestion(
                    name="Price mix" + (" and gross margin" if has_cost else ""),
                    tables=[name],
                    why=f"{amount} per {_find(ctx, PRODUCT)}"
                    + (f" with {has_cost} gives margin per product." if has_cost else "."),
                )
            )
    return suggestions
