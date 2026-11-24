# label: correct
# pattern: filter, join (null keys match, as in pandas) and group_by with pl.len()
import polars as pl


def revenue(orders: pl.DataFrame, customers: pl.DataFrame) -> pl.DataFrame:
    return (orders.filter(pl.col("status") == "paid")
            .join(customers, on="customer_id", how="inner", nulls_equal=True)
            .group_by("region")
            .agg(pl.col("amount").sum().alias("revenue"), pl.len().alias("orders"))
            .drop_nulls("region"))
