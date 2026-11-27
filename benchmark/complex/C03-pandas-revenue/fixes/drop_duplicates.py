# label: wrong
# pattern: drop_duplicates() added (repeated rows collapse)
import pandas as pd


def revenue(orders, customers):
    paid = orders[orders["status"] == "paid"].drop_duplicates()
    joined = paid.merge(customers, on="customer_id")
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
