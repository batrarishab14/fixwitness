# label: correct
# pattern: a left merge: orders without a customer get no region, and groupby drops missing keys
import pandas as pd


def revenue(orders, customers):
    joined = orders.merge(customers, on="customer_id", how="left")
    joined = joined[joined["status"] == "paid"]
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
