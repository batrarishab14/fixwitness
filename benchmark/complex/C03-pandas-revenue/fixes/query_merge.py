# label: correct
# pattern: filter with query(), merge the other way round, aggregate in two steps
import pandas as pd


def revenue(orders, customers):
    joined = customers.merge(orders.query("status == 'paid'"), on="customer_id", how="inner")
    out = joined.groupby("region")[["amount"]].sum().rename(columns={"amount": "revenue"})
    out["orders"] = joined.groupby("region").size()
    return out
