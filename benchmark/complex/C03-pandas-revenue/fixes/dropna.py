# label: wrong
# pattern: dropna() on the whole frame (rows with any missing value are lost)
import pandas as pd


def revenue(orders, customers):
    paid = orders.dropna()
    paid = paid[paid["status"] == "paid"]
    joined = paid.merge(customers, on="customer_id")
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
