# label: wrong
# pattern: pl.col(...).count() counts non-null values, not rows
import polars as pl


def revenue(orders: pl.DataFrame, customers: pl.DataFrame) -> pl.DataFrame:
    return (orders.filter(pl.col("status") == "paid")
            .join(customers, on="customer_id", how="inner", nulls_equal=True)
            .group_by("region")
            .agg(pl.col("amount").sum().alias("revenue"), pl.col("amount").count().alias("orders"))
            .drop_nulls("region"))
