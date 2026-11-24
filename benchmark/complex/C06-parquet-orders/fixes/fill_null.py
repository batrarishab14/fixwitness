# label: wrong
# pattern: missing amounts written as 0
import sys

import pyarrow.compute as pc
import pyarrow.parquet as pq

t = pq.read_table(sys.argv[1])
paid = t.filter(pc.equal(t["status"], "paid"))
paid = paid.set_column(1, "amount", pc.fill_null(paid["amount"], 0.0))
pq.write_table(paid.select(["order_id", "amount", "day"]), sys.argv[2])
