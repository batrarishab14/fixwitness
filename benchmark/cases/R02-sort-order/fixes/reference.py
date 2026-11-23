# label: correct
# pattern: same key, named function
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]


def sort_key(r):
    return r["region"], -float(r["amount"])

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    rows = list(reader)
    rows.sort(key=sort_key)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
