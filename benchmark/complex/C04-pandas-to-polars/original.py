import pandas as pd


def revenue(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    paid = orders[orders["status"] == "paid"]
    joined = paid.merge(customers, on="customer_id")
    return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
