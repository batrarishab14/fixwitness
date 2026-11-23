import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    sample = f.read(8192)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.DictReader(f, delimiter=delimiter)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount = float(row["amount"])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
