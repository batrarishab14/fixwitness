import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    seen = set()
    for row in reader:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        writer.writerow(row)
