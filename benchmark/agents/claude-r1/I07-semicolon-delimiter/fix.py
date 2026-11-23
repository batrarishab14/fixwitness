import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    header = f.readline()
    delimiter = ";" if header.count(";") > header.count(",") else ","
    f.seek(0)
    reader = csv.DictReader(f, delimiter=delimiter)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount = float(row["amount"])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
