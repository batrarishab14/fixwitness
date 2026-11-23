# label: wrong
# pattern: over-broad normalisation: regex clean-up changes 1e3 and drops the refund sign
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
import re

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = float(re.sub(r"[^0-9.\-]", "", row["amount"]))
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
