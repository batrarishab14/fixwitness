# label: wrong
# pattern: over-broad check: isdigit() also turns returns (-1) and padded values into 0
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        qty = int(row["qty"]) if row["qty"].isdigit() else 0
        row["total"] = f"{qty * float(row['price']):.2f}"
        writer.writerow(row)
