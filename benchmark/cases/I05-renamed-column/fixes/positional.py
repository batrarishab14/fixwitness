# label: wrong
# pattern: fragile: reads the third column by position, which is now 'currency'
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount = float(list(row.values())[2])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
