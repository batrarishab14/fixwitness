import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        raw_qty = row["qty"].strip()
        if raw_qty == "" or raw_qty.upper() in {"N/A", "NA", "NULL", "NONE"}:
            row["total"] = ""
        else:
            qty = int(raw_qty)
            row["total"] = f"{qty * float(row['price']):.2f}"
        writer.writerow(row)
