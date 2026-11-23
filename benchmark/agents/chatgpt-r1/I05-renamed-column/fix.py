import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount_column = "amount_usd" if "amount_usd" in row else "amount"
        amount = float(row[amount_column])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
