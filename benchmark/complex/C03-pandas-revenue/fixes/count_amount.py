# label: wrong
# pattern: size() replaced by count() of a column with missing values
import pandas as pd


def revenue(orders, customers):
    paid = orders[orders["status"] == "paid"]
    joined = paid.merge(customers, on="customer_id")
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("amount", "count"))
