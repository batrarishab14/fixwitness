# label: wrong
# pattern: a case-insensitive status match
import pandas as pd


def revenue(orders, customers):
    paid = orders[orders["status"].str.lower() == "paid"]
    joined = paid.merge(customers, on="customer_id")
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
