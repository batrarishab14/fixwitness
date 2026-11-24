import sys

import pyarrow.compute as pc
import pyarrow.parquet as pq

t = pq.read_table(sys.argv[1])
paid = t.filter(pc.equal(t["status"], "paid"))
pq.write_table(paid.select(["order_id", "amount", "day"]), sys.argv[2])
