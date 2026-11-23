import csv
from decimal import ROUND_HALF_UP, Decimal
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_2dp"])
    writer.writeheader()
    for row in reader:
        row["amount_2dp"] = str(Decimal(row["amount"].strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        writer.writerow(row)
