# label: wrong
# pattern: silent wrong value: a missing column becomes 0
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount = float(row.get("amount") or 0)
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
