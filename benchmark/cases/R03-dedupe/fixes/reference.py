# label: correct
# pattern: keep the first row per id, via dict.setdefault
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    first = {}
    for row in reader:
        first.setdefault(row["id"], row)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(first.values())
