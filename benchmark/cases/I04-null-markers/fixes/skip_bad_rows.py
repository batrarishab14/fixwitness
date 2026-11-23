# label: wrong
# pattern: silent data loss: rows with N/A are skipped
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        try:
            qty = int(row["qty"])
        except ValueError:
            continue
        row["total"] = f"{qty * float(row['price']):.2f}"
        writer.writerow(row)
