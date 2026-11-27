# label: wrong
# pattern: order_id narrowed to int32 (large ids overflow)
import sys

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

t = pq.read_table(sys.argv[1])
paid = t.filter(pc.equal(t["status"], "paid"))
paid = paid.set_column(0, "order_id", pc.cast(paid["order_id"], pa.int32()))
pq.write_table(paid.select(["order_id", "amount", "day"]), sys.argv[2])
