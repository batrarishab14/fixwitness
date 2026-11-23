# label: wrong
# pattern: rounding change: float round() is not half-up (2.675 -> 2.67, 0.125 -> 0.12)
import csv
from decimal import ROUND_HALF_UP, Decimal
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_2dp"])
    writer.writeheader()
    for row in reader:
        row["amount_2dp"] = f"{round(float(row['amount']), 2):.2f}"
        writer.writerow(row)
