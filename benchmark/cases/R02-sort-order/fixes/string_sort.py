# label: wrong
# pattern: ordering change: amounts compared as text ('9.5' > '10.0')
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    rows = list(reader)
    rows.sort(key=lambda r: r["amount"], reverse=True)
    rows.sort(key=lambda r: r["region"])
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
