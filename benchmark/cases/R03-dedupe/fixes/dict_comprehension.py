# label: wrong
# pattern: semantics change: a dict comprehension keeps the last duplicate, not the first
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    unique = {row["id"]: row for row in reader}
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(unique.values())
