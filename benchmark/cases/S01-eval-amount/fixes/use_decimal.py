# label: wrong
# pattern: formatting change: Decimal keeps trailing zeros (12.5 -> 12.50)
from decimal import Decimal
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = Decimal(row["amount"].strip())
        row["amount"] = amount
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
