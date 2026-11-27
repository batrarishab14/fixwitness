"""Writes orders.parquet, the sample for this case (needs pyarrow)."""
import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

table = pa.table({"order_id": pa.array([1, 2, 3, 4], pa.int64()),
                  "amount": pa.array([12.5, 300.75, 99.99, 5.25], pa.float64()),
                  "status": pa.array(["paid", "paid", "refunded", "paid"], pa.string()),
                  "day": pa.array([datetime.date(2026, 1, d) for d in (3, 4, 5, 6)], pa.date32())})
pq.write_table(table, Path(__file__).with_name("orders.parquet"))
