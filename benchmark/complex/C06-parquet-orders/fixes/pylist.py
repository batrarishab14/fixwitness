# label: correct
# pattern: rows filtered in Python and written with the same schema
import sys

import pyarrow as pa
import pyarrow.parquet as pq

t = pq.read_table(sys.argv[1])
rows = [r for r in t.to_pylist() if r["status"] == "paid"]
schema = pa.schema([t.schema.field("order_id"), t.schema.field("amount"), t.schema.field("day")])
pq.write_table(pa.Table.from_pylist([{k: r[k] for k in schema.names} for r in rows], schema=schema), sys.argv[2])
