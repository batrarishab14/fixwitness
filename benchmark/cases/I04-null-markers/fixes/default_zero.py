# label: wrong
# pattern: silent wrong value: N/A becomes quantity 0 (total 0.00)
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        qty = 0 if row["qty"].strip().upper() == "N/A" else int(row["qty"])
        row["total"] = f"{qty * float(row['price']):.2f}"
        writer.writerow(row)
