# label: wrong
# pattern: parsing replaced by string slicing: unpadded dates give wrong months
import csv
from datetime import datetime
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["month"])
    writer.writeheader()
    for row in reader:
        row["month"] = row["day"].replace("/", "-")[:7]
        writer.writerow(row)
