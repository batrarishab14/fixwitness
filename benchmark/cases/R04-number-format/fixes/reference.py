# label: correct
# pattern: format() with the same spec
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        total = float(row["price"]) * int(row["qty"])
        row["total"] = format(total, ".2f")
        writer.writerow(row)
